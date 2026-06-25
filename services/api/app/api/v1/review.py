from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, nullsfirst, or_, select
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
    domain_slug: str | None = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> list[ReviewItem]:
    now = datetime.utcnow()
    domain_query = select(DomainPack)
    if domain_slug:
        domain_query = domain_query.where(DomainPack.slug == domain_slug)
    else:
        domain_query = domain_query.order_by(desc(DomainPack.created_at))
    active_domain = db.scalar(domain_query)
    if domain_slug and active_domain is None:
        raise HTTPException(status_code=404, detail="Course not found.")

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
    if active_domain is not None:
        due_states = [state for state in due_states if state.skill and state.skill.domain_id == active_domain.id]
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

    learned_state_query = (
        select(LearnerSkillState.skill_id)
        .join(SkillNode, SkillNode.id == LearnerSkillState.skill_id)
        .where(
            LearnerSkillState.user_id == user_id,
            or_(
                LearnerSkillState.evidence_count > 0,
                LearnerSkillState.mastery > 0,
            ),
        )
    )
    if active_domain is not None:
        learned_state_query = learned_state_query.where(
            SkillNode.domain_id == active_domain.id
        )

    seen_skill_ids = {item.skill.id for item in items}
    learned_skill_ids = set(db.scalars(learned_state_query).all())
    excluded_skill_ids = seen_skill_ids | learned_skill_ids
    fresh_query = select(SkillNode)
    if active_domain is not None:
        fresh_query = fresh_query.where(SkillNode.domain_id == active_domain.id)
    if excluded_skill_ids:
        fresh_query = fresh_query.where(SkillNode.id.not_in(excluded_skill_ids))

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
