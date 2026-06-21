import asyncio
import hashlib
import json
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.models import ContentImport, DomainPack, LearnerSkillState, MasteryEvidence, SkillEdge, SkillNode
from app.schemas import ContentImportCreateRead, ContentImportRead, DomainPackRead
from app.services.content_parser import extract_upload_content
from app.services.content_parser import ExtractedContent
from app.services.course_generator import (
    CourseGenerationError,
    CourseGenerationPaused,
    GeneratedDomainPack,
    generate_course_pack,
)

router = APIRouter()


@router.get("", response_model=list[ContentImportRead])
def list_imports(db: Session = Depends(get_db)) -> list[ContentImport]:
    return list(db.scalars(select(ContentImport).order_by(desc(ContentImport.created_at)).limit(20)).all())


@router.get("/{import_id}", response_model=ContentImportRead)
def get_import(import_id: str, db: Session = Depends(get_db)) -> ContentImport:
    import_record = db.get(ContentImport, import_id)
    if import_record is None:
        raise HTTPException(status_code=404, detail="Import not found.")
    return import_record


@router.post("", response_model=ContentImportCreateRead)
async def create_import(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    domain_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> ContentImportCreateRead:
    filename = file.filename or "upload"
    domain = db.get(DomainPack, domain_id) if domain_id else None
    if domain_id and domain is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    file_bytes = await file.read()
    file_sha256 = hashlib.sha256(file_bytes).hexdigest()
    existing = _find_reusable_import(db, file_sha256=file_sha256, domain_id=domain.id if domain else None)
    if existing is not None:
        if existing.status in {"paused", "failed"}:
            existing.status = "queued"
            existing.control_requested = ""
            existing.error = ""
            existing.current_step = "Resume queued."
            existing.completed_at = None
            db.commit()
            db.refresh(existing)
            background_tasks.add_task(_run_import, existing.id, file_bytes, filename, domain.id if domain else None)
        return ContentImportCreateRead(
            import_record=ContentImportRead.model_validate(existing),
            domain=DomainPackRead.model_validate(domain) if domain else None,
            skill_count=0,
            question_count=0,
        )

    import_record = ContentImport(
        filename=filename,
        content_type=file.content_type or "",
        file_sha256=file_sha256,
        status="extracting",
        domain_id=domain.id if domain else None,
        current_step="Parsing file.",
    )
    db.add(import_record)
    db.commit()
    db.refresh(import_record)

    background_tasks.add_task(_run_import, import_record.id, file_bytes, filename, domain.id if domain else None)

    return ContentImportCreateRead(
        import_record=ContentImportRead.model_validate(import_record),
        domain=DomainPackRead.model_validate(domain),
        skill_count=0,
        question_count=0,
    )


@router.post("/{import_id}/pause", response_model=ContentImportRead)
def pause_import(import_id: str, db: Session = Depends(get_db)) -> ContentImport:
    import_record = db.get(ContentImport, import_id)
    if import_record is None:
        raise HTTPException(status_code=404, detail="Import not found.")
    if import_record.status in {"published", "failed", "paused"}:
        return import_record
    import_record.control_requested = "pause"
    import_record.status = "pause_requested"
    import_record.current_step = "Pause requested; waiting for the current segment to finish."
    db.commit()
    db.refresh(import_record)
    return import_record


@router.post("/{import_id}/resume", response_model=ContentImportRead)
def resume_import(
    import_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ContentImport:
    import_record = db.get(ContentImport, import_id)
    if import_record is None:
        raise HTTPException(status_code=404, detail="Import not found.")
    if import_record.status == "pause_requested":
        import_record.status = "generating"
        import_record.control_requested = ""
        import_record.current_step = "Pause cancelled; generation is still running."
        db.commit()
        db.refresh(import_record)
        return import_record
    if import_record.status in {"published", "extracting", "generating", "publishing", "queued"}:
        return import_record
    if not import_record.extracted_text:
        raise HTTPException(status_code=400, detail="This import has no parsed text. Upload the same file again to resume.")
    import_record.status = "queued"
    import_record.control_requested = ""
    import_record.error = ""
    import_record.current_step = "Resume queued."
    import_record.completed_at = None
    db.commit()
    db.refresh(import_record)
    background_tasks.add_task(_run_import, import_record.id, b"", import_record.filename, import_record.domain_id)
    return import_record


def _run_import(import_id: str, file_bytes: bytes, filename: str, domain_id: str | None) -> None:
    db = SessionLocal()
    import_record: ContentImport | None = None
    try:
        import_record = db.get(ContentImport, import_id)
        if import_record is None:
            return
        domain = db.get(DomainPack, domain_id) if domain_id else None
        import_record.status = "extracting"
        import_record.current_step = "Parsing file."
        import_record.completed_at = None
        db.commit()

        if import_record.extracted_text:
            extracted = ExtractedContent(text=import_record.extracted_text, pages=[], images=[])
        else:
            if not file_bytes:
                raise CourseGenerationError("No uploaded file bytes are available. Upload the same file again to resume.")
            upload = UploadFile(filename=filename, file=BytesIO(file_bytes))
            extracted = asyncio.run(extract_upload_content(upload))
            import_record.extracted_text = extracted.text
        import_record.status = "generating"
        import_record.current_step = f"Parsed text and {len(extracted.images)} images."
        db.commit()

        def update_progress(*, total: int, processed: int, step: str) -> None:
            db.refresh(import_record)
            if import_record.control_requested == "pause":
                raise CourseGenerationPaused("Generation paused.")
            import_record.total_segments = total
            import_record.processed_segments = processed
            import_record.current_step = step
            db.commit()

        def save_segment(*, index: int, pack: GeneratedDomainPack, packs: list[GeneratedDomainPack]) -> None:
            import_record.segment_packs_json = json.dumps(
                [item.model_dump() for item in packs],
                ensure_ascii=False,
            )
            import_record.processed_segments = index
            import_record.current_step = f"Saved segment {index}/{import_record.total_segments or index}."
            db.commit()

        def should_pause() -> bool:
            db.refresh(import_record)
            return import_record.control_requested == "pause"

        existing_packs = _load_segment_packs(import_record)
        generated = generate_course_pack(
            content=extracted,
            filename=filename,
            course_name=domain.name if domain else None,
            progress_callback=update_progress,
            segment_callback=save_segment,
            should_pause=should_pause,
            existing_packs=existing_packs,
        )
        import_record.generated_json = generated.model_dump_json()
        import_record.status = "publishing"
        import_record.current_step = "Publishing generated course."
        db.commit()

        domain, skill_count, question_count = publish_generated_pack(db, generated, target_domain=domain)
        import_record.domain_id = domain.id
        import_record.status = "published"
        import_record.current_step = "Generation completed."
        import_record.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(import_record)
        db.refresh(domain)
    except CourseGenerationPaused:
        if import_record is not None:
            import_record.status = "paused"
            import_record.control_requested = ""
            import_record.current_step = "Paused. Resume will continue from saved segments."
            db.commit()
    except HTTPException as exc:
        if import_record is not None:
            _mark_failed(db, import_record, str(exc.detail))
    except CourseGenerationError as exc:
        if import_record is not None:
            _mark_failed(db, import_record, str(exc))
    except Exception as exc:
        if import_record is not None:
            _mark_failed(db, import_record, f"Import failed: {exc}")
    finally:
        db.close()


def _find_reusable_import(
    db: Session,
    *,
    file_sha256: str,
    domain_id: str | None,
) -> ContentImport | None:
    if not file_sha256:
        return None
    stmt = (
        select(ContentImport)
        .where(ContentImport.file_sha256 == file_sha256)
        .where(ContentImport.domain_id == domain_id if domain_id is not None else ContentImport.domain_id.is_(None))
        .where(ContentImport.status.in_(["extracting", "queued", "generating", "pause_requested", "paused", "failed", "publishing"]))
        .order_by(desc(ContentImport.created_at))
    )
    return db.scalar(stmt)


def _load_segment_packs(import_record: ContentImport) -> list[GeneratedDomainPack]:
    if not import_record.segment_packs_json:
        return []
    try:
        data = json.loads(import_record.segment_packs_json)
    except ValueError:
        return []
    if not isinstance(data, list):
        return []
    packs: list[GeneratedDomainPack] = []
    for item in data:
        try:
            packs.append(GeneratedDomainPack.model_validate(item))
        except Exception:
            continue
    return packs


def publish_generated_pack(
    db: Session,
    generated: GeneratedDomainPack,
    *,
    target_domain: DomainPack | None = None,
) -> tuple[DomainPack, int, int]:
    if target_domain is None:
        slug = _unique_domain_slug(db, generated.slug)
        domain = DomainPack(
            slug=slug,
            name=generated.name,
            version=generated.version,
            description=generated.description,
        )
        db.add(domain)
    else:
        domain = target_domain
        _clear_domain_content(db, domain.id)
        domain.description = generated.description or domain.description
        domain.version = generated.version
    db.flush()

    skill_by_slug: dict[str, SkillNode] = {}
    question_count = 0
    for index, item in enumerate(sorted(generated.skills, key=lambda skill: skill.order_index), start=1):
        questions = [question.model_dump() for question in item.questions]
        question_count += len(questions)
        skill = SkillNode(
            domain_id=domain.id,
            slug=item.slug,
            title=item.title,
            summary=item.summary,
            kind=item.kind,
            difficulty=item.difficulty,
            estimated_minutes=item.estimated_minutes,
            content=item.lesson_explain,
            lesson_explain=item.lesson_explain,
            key_points_json=json.dumps(item.key_points, ensure_ascii=False),
            questions_json=json.dumps(questions, ensure_ascii=False),
            order_index=index,
        )
        db.add(skill)
        skill_by_slug[item.slug] = skill

    db.flush()
    for item in generated.skills:
        skill = skill_by_slug[item.slug]
        for prereq_slug in item.prerequisites:
            prereq = skill_by_slug.get(prereq_slug)
            if prereq is not None:
                db.add(
                    SkillEdge(
                        domain_id=domain.id,
                        prerequisite_skill_id=prereq.id,
                        skill_id=skill.id,
                    )
                )

    db.commit()
    return domain, len(skill_by_slug), question_count


def _unique_domain_slug(db: Session, slug: str) -> str:
    candidate = slug
    index = 2
    while db.scalar(select(DomainPack).where(DomainPack.slug == candidate)) is not None:
        candidate = f"{slug}_{index}"
        index += 1
    return candidate


def _mark_failed(db: Session, import_record: ContentImport, error: str) -> None:
    import_record.status = "failed"
    import_record.control_requested = ""
    import_record.error = error
    import_record.current_step = "Generation failed."
    import_record.completed_at = datetime.utcnow()
    db.commit()


def _clear_domain_content(db: Session, domain_id: str) -> None:
    skill_ids = list(db.scalars(select(SkillNode.id).where(SkillNode.domain_id == domain_id)).all())
    if skill_ids:
        db.query(MasteryEvidence).filter(MasteryEvidence.skill_id.in_(skill_ids)).delete(synchronize_session=False)
        db.query(LearnerSkillState).filter(LearnerSkillState.skill_id.in_(skill_ids)).delete(synchronize_session=False)
    db.query(SkillEdge).filter(SkillEdge.domain_id == domain_id).delete(synchronize_session=False)
    db.query(SkillNode).filter(SkillNode.domain_id == domain_id).delete(synchronize_session=False)
