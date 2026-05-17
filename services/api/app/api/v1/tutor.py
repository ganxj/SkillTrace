from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_user_id
from app.db.session import get_db
from app.models import SkillNode, TutorMessage
from app.schemas import TutorMessageCreate, TutorMessageRead
from app.services.tutor import TutorProviderError, get_tutor_provider

router = APIRouter()


@router.post("/messages", response_model=TutorMessageRead)
def create_tutor_message(
    payload: TutorMessageCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> TutorMessageRead:
    skill_title = None
    if payload.skill_id:
        skill = db.scalar(select(SkillNode).where(SkillNode.id == payload.skill_id))
        skill_title = skill.title if skill else None

    user_message = TutorMessage(
        user_id=user_id,
        session_id=payload.session_id,
        role="user",
        content=payload.message,
        provider="user",
    )
    db.add(user_message)
    db.flush()

    provider = get_tutor_provider()
    try:
        response = provider.generate(
            message=payload.message,
            mode=payload.mode,
            skill_title=skill_title,
        )
    except TutorProviderError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    assistant_message = TutorMessage(
        user_id=user_id,
        session_id=payload.session_id,
        role="assistant",
        content=response,
        provider=provider.name,
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)
    return TutorMessageRead(
        response=response,
        provider=provider.name,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
    )

