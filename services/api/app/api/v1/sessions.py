from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.deps import get_user_id
from app.db.session import get_db
from app.models import LearningSession
from app.schemas import LearningSessionCreate, LearningSessionRead

router = APIRouter()


@router.post("", response_model=LearningSessionRead)
def create_session(
    payload: LearningSessionCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> LearningSession:
    session = LearningSession(user_id=user_id, **payload.model_dump())
    if payload.mode == "review":
        session.completed_at = datetime.utcnow()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

