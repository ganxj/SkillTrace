from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DomainPackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    version: str
    description: str


class DomainPackCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = ""


class QuizQuestionRead(BaseModel):
    prompt: str
    options: list[str]
    correct_index: int
    explanation: str


class SkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    domain_id: str
    slug: str
    title: str
    summary: str
    kind: str
    difficulty: int
    estimated_minutes: int
    content: str
    lesson_explain: str = ""
    key_points: list[str] = Field(default_factory=list)
    questions: list[QuizQuestionRead] = Field(default_factory=list)
    order_index: int
    prerequisites: list[str] = Field(default_factory=list)


class LearningSessionCreate(BaseModel):
    domain_id: str | None = None
    skill_id: str | None = None
    mode: str = "learn"
    duration_minutes: int = Field(default=5, ge=1, le=120)
    goal: str = ""


class LearningSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    domain_id: str | None
    skill_id: str | None
    mode: str
    duration_minutes: int
    goal: str
    reflection: str
    created_at: datetime
    completed_at: datetime | None


class MasteryEvidenceCreate(BaseModel):
    skill_id: str
    session_id: str | None = None
    evidence_type: str = "quiz"
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    prompt: str = ""
    response: str = ""
    feedback: str = ""


class MasteryEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    skill_id: str
    session_id: str | None
    evidence_type: str
    score: float
    confidence_delta: float
    mastery_delta: float
    prompt: str
    response: str
    feedback: str
    created_at: datetime


class LearnerSkillStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    skill_id: str
    mastery: float
    confidence: float
    last_seen_at: datetime | None
    review_due_at: datetime | None
    evidence_count: int
    updated_at: datetime
    skill: SkillRead | None = None


class ReviewItem(BaseModel):
    skill: SkillRead
    state: LearnerSkillStateRead | None = None
    reason: str


class TutorMessageCreate(BaseModel):
    session_id: str | None = None
    skill_id: str | None = None
    message: str
    mode: str = "coach"


class TutorMessageRead(BaseModel):
    response: str
    provider: str
    user_message_id: str
    assistant_message_id: str


class ContentImportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    content_type: str
    status: str
    error: str
    domain_id: str | None
    total_segments: int = 0
    processed_segments: int = 0
    current_step: str = ""
    created_at: datetime
    completed_at: datetime | None
    domain: DomainPackRead | None = None


class ContentImportCreateRead(BaseModel):
    import_record: ContentImportRead
    domain: DomainPackRead
    skill_count: int
    question_count: int
