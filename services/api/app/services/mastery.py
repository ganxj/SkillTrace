from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LearnerSkillState, MasteryEvidence
from app.schemas import MasteryEvidenceCreate


EVIDENCE_WEIGHTS = {
    "quiz": 0.08,
    "explain": 0.12,
    "transfer": 0.16,
    "micro_project": 0.18,
    "review": 0.06,
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def review_interval_days(mastery: float, confidence: float) -> int:
    if mastery < 0.35 or confidence < 0.3:
        return 1
    if mastery < 0.65:
        return 3
    if mastery < 0.85:
        return 7
    return 14


def record_evidence(
    db: Session,
    user_id: str,
    payload: MasteryEvidenceCreate,
) -> tuple[MasteryEvidence, LearnerSkillState]:
    state = db.scalar(
        select(LearnerSkillState).where(
            LearnerSkillState.user_id == user_id,
            LearnerSkillState.skill_id == payload.skill_id,
        )
    )
    if state is None:
        state = LearnerSkillState(user_id=user_id, skill_id=payload.skill_id)
        db.add(state)
        db.flush()

    weight = EVIDENCE_WEIGHTS.get(payload.evidence_type, 0.08)
    centered_score = payload.score - 0.5
    mastery_delta = centered_score * weight
    confidence_delta = 0.05 + max(payload.score, 0.0) * 0.05

    now = datetime.utcnow()
    state.mastery = clamp(state.mastery + mastery_delta)
    state.confidence = clamp(state.confidence + confidence_delta)
    state.last_seen_at = now
    state.review_due_at = now + timedelta(days=review_interval_days(state.mastery, state.confidence))
    state.evidence_count += 1
    state.updated_at = now

    evidence = MasteryEvidence(
        user_id=user_id,
        skill_id=payload.skill_id,
        session_id=payload.session_id,
        evidence_type=payload.evidence_type,
        score=payload.score,
        confidence_delta=confidence_delta,
        mastery_delta=mastery_delta,
        prompt=payload.prompt,
        response=payload.response,
        feedback=payload.feedback,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    db.refresh(state)
    return evidence, state

