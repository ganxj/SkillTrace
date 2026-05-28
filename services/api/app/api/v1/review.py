from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import desc, nullsfirst, select
from sqlalchemy.orm import Session, joinedload

from app.api.v1.deps import get_user_id
from app.api.v1.skills import prerequisites_by_skill, skill_to_read
from app.db.session import get_db
from app.models import DomainPack, LearnerSkillState, SkillNode
from app.schemas import LearnerSkillStateRead, ReviewItem

router = APIRouter()


@router.get("/next", response_model=list[ReviewItem])
def next_review(
    limit: int = 5,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> list[ReviewItem]:
    now = datetime.utcnow()
    latest_domain = db.scalar(select(DomainPack).order_by(desc(DomainPack.created_at)))
    due_states = list(
        db.scalars(
            select(LearnerSkillState)
            .options(joinedload(LearnerSkillState.skill))
            .where(LearnerSkillState.user_id == user_id)
            .order_by(
                nullsfirst(LearnerSkillState.review_due_at),
                LearnerSkillState.mastery,
                LearnerSkillState.confidence,
            )
            .limit(limit)
        ).all()
    )
    if latest_domain is not None:
        due_states = [state for state in due_states if state.skill and state.skill.domain_id == latest_domain.id]
    due_states = [state for state in due_states if state.review_due_at is None or state.review_due_at <= now]

    items: list[ReviewItem] = []
    skill_ids = [state.skill_id for state in due_states]
    prereq_map = prerequisites_by_skill(db, skill_ids)
    for state in due_states[:limit]:
        reason = "到期复习" if state.review_due_at and state.review_due_at <= now else "低掌握度优先"
        items.append(
            ReviewItem(
                skill=skill_to_read(state.skill, prereq_map.get(state.skill_id, [])),
                state=LearnerSkillStateRead.model_validate(state),
                reason=reason,
            )
        )

    if len(items) >= limit:
        return items

    seen_skill_ids = {item.skill.id for item in items}
    fresh_query = select(SkillNode)
    if latest_domain is not None:
        fresh_query = fresh_query.where(SkillNode.domain_id == latest_domain.id)
    if seen_skill_ids:
        fresh_query = fresh_query.where(SkillNode.id.not_in(seen_skill_ids))

    fresh_skills = list(
        db.scalars(
            fresh_query.order_by(SkillNode.order_index, SkillNode.difficulty).limit(limit - len(items))
        ).all()
    )
    fresh_prereqs = prerequisites_by_skill(db, [skill.id for skill in fresh_skills])
    for skill in fresh_skills:
        items.append(
            ReviewItem(
                skill=skill_to_read(skill, fresh_prereqs.get(skill.id, [])),
                state=None,
                reason="新知识点",
            )
        )
    return items
