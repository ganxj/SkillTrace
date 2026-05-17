from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import DomainPack, SkillEdge, SkillNode
from app.schemas import SkillRead

router = APIRouter()


@router.get("", response_model=list[SkillRead])
def list_skills(
    domain_slug: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[SkillRead]:
    query = select(SkillNode).order_by(SkillNode.order_index, SkillNode.title)
    if domain_slug:
        domain = db.scalar(select(DomainPack).where(DomainPack.slug == domain_slug))
        if domain is None:
            return []
        query = query.where(SkillNode.domain_id == domain.id)
    skills = list(db.scalars(query).all())
    prereq_map = prerequisites_by_skill(db, [skill.id for skill in skills])
    return [SkillRead.model_validate(skill).model_copy(update={"prerequisites": prereq_map[skill.id]}) for skill in skills]


def prerequisites_by_skill(db: Session, skill_ids: list[str]) -> dict[str, list[str]]:
    result = {skill_id: [] for skill_id in skill_ids}
    if not skill_ids:
        return result
    rows = db.execute(
        select(SkillEdge.skill_id, SkillNode.slug)
        .join(SkillNode, SkillNode.id == SkillEdge.prerequisite_skill_id)
        .where(SkillEdge.skill_id.in_(skill_ids))
    ).all()
    for skill_id, prereq_slug in rows:
        result[skill_id].append(prereq_slug)
    return result

