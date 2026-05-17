from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.v1.deps import get_user_id
from app.db.session import get_db
from app.models import LearnerSkillState
from app.schemas import LearnerSkillStateRead

router = APIRouter()


@router.get("/state", response_model=list[LearnerSkillStateRead])
def list_state(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> list[LearnerSkillState]:
    return list(
        db.scalars(
            select(LearnerSkillState)
            .options(joinedload(LearnerSkillState.skill))
            .where(LearnerSkillState.user_id == user_id)
            .order_by(LearnerSkillState.updated_at.desc())
        ).all()
    )

