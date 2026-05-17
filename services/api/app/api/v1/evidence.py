from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.v1.deps import get_user_id
from app.db.session import get_db
from app.models import MasteryEvidence
from app.schemas import MasteryEvidenceCreate, MasteryEvidenceRead
from app.services.mastery import record_evidence

router = APIRouter()


@router.post("", response_model=MasteryEvidenceRead)
def create_evidence(
    payload: MasteryEvidenceCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> MasteryEvidence:
    evidence, _state = record_evidence(db, user_id, payload)
    return evidence


@router.get("", response_model=list[MasteryEvidenceRead])
def list_evidence(
    limit: int = 30,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id),
) -> list[MasteryEvidence]:
    return list(
        db.scalars(
            select(MasteryEvidence)
            .where(MasteryEvidence.user_id == user_id)
            .order_by(desc(MasteryEvidence.created_at))
            .limit(limit)
        ).all()
    )

