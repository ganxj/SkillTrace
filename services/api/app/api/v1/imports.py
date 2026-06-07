import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ContentImport, DomainPack, LearnerSkillState, MasteryEvidence, SkillEdge, SkillNode
from app.schemas import ContentImportCreateRead, ContentImportRead, DomainPackRead
from app.services.content_parser import extract_upload_content
from app.services.course_generator import CourseGenerationError, GeneratedDomainPack, generate_course_pack

router = APIRouter()


@router.get("", response_model=list[ContentImportRead])
def list_imports(db: Session = Depends(get_db)) -> list[ContentImport]:
    return list(db.scalars(select(ContentImport).order_by(desc(ContentImport.created_at)).limit(20)).all())


@router.post("", response_model=ContentImportCreateRead)
async def create_import(
    file: UploadFile = File(...),
    domain_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> ContentImportCreateRead:
    filename = file.filename or "upload"
    domain = db.get(DomainPack, domain_id) if domain_id else None
    if domain_id and domain is None:
        raise HTTPException(status_code=404, detail="Course not found.")

    import_record = ContentImport(
        filename=filename,
        content_type=file.content_type or "",
        status="extracting",
        domain_id=domain.id if domain else None,
        current_step="正在解析文件",
    )
    db.add(import_record)
    db.commit()
    db.refresh(import_record)

    try:
        extracted = await extract_upload_content(file)
        import_record.extracted_text = extracted.text
        import_record.status = "generating"
        import_record.current_step = f"已解析文本和 {len(extracted.images)} 张图片"
        db.commit()

        def update_progress(*, total: int, processed: int, step: str) -> None:
            import_record.total_segments = total
            import_record.processed_segments = processed
            import_record.current_step = step
            db.commit()

        generated = generate_course_pack(
            content=extracted,
            filename=filename,
            course_name=domain.name if domain else None,
            progress_callback=update_progress,
        )
        import_record.generated_json = generated.model_dump_json()
        import_record.status = "publishing"
        import_record.current_step = "正在发布课程内容"
        db.commit()

        domain, skill_count, question_count = publish_generated_pack(db, generated, target_domain=domain)
        import_record.domain_id = domain.id
        import_record.status = "published"
        import_record.current_step = "生成完成"
        import_record.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(import_record)
        db.refresh(domain)

        return ContentImportCreateRead(
            import_record=ContentImportRead.model_validate(import_record),
            domain=DomainPackRead.model_validate(domain),
            skill_count=skill_count,
            question_count=question_count,
        )
    except HTTPException as exc:
        _mark_failed(db, import_record, str(exc.detail))
        raise
    except CourseGenerationError as exc:
        _mark_failed(db, import_record, str(exc))
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        _mark_failed(db, import_record, str(exc))
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}") from exc


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
    import_record.error = error
    import_record.current_step = "生成失败"
    import_record.completed_at = datetime.utcnow()
    db.commit()


def _clear_domain_content(db: Session, domain_id: str) -> None:
    skill_ids = list(db.scalars(select(SkillNode.id).where(SkillNode.domain_id == domain_id)).all())
    if skill_ids:
        db.query(MasteryEvidence).filter(MasteryEvidence.skill_id.in_(skill_ids)).delete(synchronize_session=False)
        db.query(LearnerSkillState).filter(LearnerSkillState.skill_id.in_(skill_ids)).delete(synchronize_session=False)
    db.query(SkillEdge).filter(SkillEdge.domain_id == domain_id).delete(synchronize_session=False)
    db.query(SkillNode).filter(SkillNode.domain_id == domain_id).delete(synchronize_session=False)
