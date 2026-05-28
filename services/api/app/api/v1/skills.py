import json

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
    return [skill_to_read(skill, prereq_map[skill.id]) for skill in skills]


def skill_to_read(skill: SkillNode, prerequisites: list[str]) -> SkillRead:
    return SkillRead.model_validate(skill).model_copy(
        update={
            "lesson_explain": skill.lesson_explain or skill.content,
            "key_points": _load_json_list(skill.key_points_json),
            "questions": _load_json_list(skill.questions_json),
            "prerequisites": prerequisites,
        }
    )


def _load_json_list(value: str | None) -> list:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


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
