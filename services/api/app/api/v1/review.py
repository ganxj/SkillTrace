from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import nullsfirst, select
from sqlalchemy.orm import Session, joinedload

from app.api.v1.deps import get_user_id
from app.api.v1.skills import prerequisites_by_skill
from app.db.session import get_db
from app.models import LearnerSkillState, SkillNode
from app.schemas import LearnerSkillStateRead, ReviewItem, SkillRead

router = APIRouter()


@router.get("/next", response_model=list[ReviewItem])
def next_review(
    limit: int = 5,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> list[ReviewItem]:
    now = datetime.utcnow()
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
    due_states = [state for state in due_states if state.review_due_at is None or state.review_due_at <= now]

    items: list[ReviewItem] = []
    skill_ids = [state.skill_id for state in due_states]
    prereq_map = prerequisites_by_skill(db, skill_ids)
    for state in due_states[:limit]:
        reason = "到期复习" if state.review_due_at and state.review_due_at <= now else "低掌握度优先"
        skill = SkillRead.model_validate(state.skill).model_copy(
            update={"prerequisites": prereq_map.get(state.skill_id, [])}
        )
        items.append(
            ReviewItem(
                skill=skill,
                state=LearnerSkillStateRead.model_validate(state),
                reason=reason,
            )
        )

    if len(items) >= limit:
        return items

    seen_skill_ids = {item.skill.id for item in items}
    fresh_skills = list(
        db.scalars(
            select(SkillNode)
            .where(SkillNode.id.not_in(seen_skill_ids) if seen_skill_ids else True)
            .order_by(SkillNode.order_index, SkillNode.difficulty)
            .limit(limit - len(items))
        ).all()
    )
    fresh_prereqs = prerequisites_by_skill(db, [skill.id for skill in fresh_skills])
    for skill in fresh_skills:
        items.append(
            ReviewItem(
                skill=SkillRead.model_validate(skill).model_copy(
                    update={"prerequisites": fresh_prereqs.get(skill.id, [])}
                ),
                state=None,
                reason="新知识点",
            )
        )
    return items

