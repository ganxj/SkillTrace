from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ContentImport, DomainPack, LearnerSkillState, MasteryEvidence, SkillEdge, SkillNode
from app.schemas import DomainPackCreate, DomainPackRead

router = APIRouter()


@router.get("", response_model=list[DomainPackRead])
def list_domains(db: Session = Depends(get_db)) -> list[DomainPack]:
    return list(db.scalars(select(DomainPack).order_by(DomainPack.created_at)).all())


@router.post("", response_model=DomainPackRead)
def create_domain(payload: DomainPackCreate, db: Session = Depends(get_db)) -> DomainPack:
    domain = DomainPack(
        slug=_unique_slug(db, _slugify(payload.name) or "course"),
        name=payload.name.strip(),
        version="0.1.0",
        description=payload.description.strip(),
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


@router.get("/latest", response_model=DomainPackRead)
def latest_domain(db: Session = Depends(get_db)) -> DomainPack:
    domain = db.scalar(select(DomainPack).order_by(desc(DomainPack.created_at)))
    if domain is None:
        raise HTTPException(status_code=404, detail="No domain packs found.")
    return domain


@router.delete("/{domain_id}/content", response_model=DomainPackRead)
def clear_domain_content(domain_id: str, db: Session = Depends(get_db)) -> DomainPack:
    domain = db.get(DomainPack, domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Course not found.")
    _clear_domain_content(db, domain_id)
    db.commit()
    db.refresh(domain)
    return domain


@router.delete("/{domain_id}", response_model=DomainPackRead)
def delete_domain(domain_id: str, db: Session = Depends(get_db)) -> DomainPack:
    domain = db.get(DomainPack, domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Course not found.")
    deleted = DomainPackRead.model_validate(domain)
    _clear_domain_content(db, domain_id)
    db.query(ContentImport).filter(ContentImport.domain_id == domain_id).update(
        {ContentImport.domain_id: None},
        synchronize_session=False,
    )
    db.delete(domain)
    db.commit()
    return deleted


def _unique_slug(db: Session, slug: str) -> str:
    candidate = slug[:70] or "course"
    index = 2
    while db.scalar(select(DomainPack).where(DomainPack.slug == candidate)) is not None:
        candidate = f"{slug[:64]}_{index}"
        index += 1
    return candidate


def _clear_domain_content(db: Session, domain_id: str) -> None:
    skill_ids = list(db.scalars(select(SkillNode.id).where(SkillNode.domain_id == domain_id)).all())
    if skill_ids:
        db.query(MasteryEvidence).filter(MasteryEvidence.skill_id.in_(skill_ids)).delete(synchronize_session=False)
        db.query(LearnerSkillState).filter(LearnerSkillState.skill_id.in_(skill_ids)).delete(synchronize_session=False)
    db.query(SkillEdge).filter(SkillEdge.domain_id == domain_id).delete(synchronize_session=False)
    db.query(SkillNode).filter(SkillNode.domain_id == domain_id).delete(synchronize_session=False)


def _slugify(value: str) -> str:
    import re

    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9_]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug
