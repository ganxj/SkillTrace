from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def new_id() -> str:
    return str(uuid4())


class DomainPack(Base):
    __tablename__ = "domain_packs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    version: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    skills: Mapped[list["SkillNode"]] = relationship(back_populates="domain", cascade="all,delete")


class SkillNode(Base):
    __tablename__ = "skill_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    domain_id: Mapped[str] = mapped_column(ForeignKey("domain_packs.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(180))
    summary: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(40), default="concept")
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=5)
    content: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    domain: Mapped[DomainPack] = relationship(back_populates="skills")

    __table_args__ = (UniqueConstraint("domain_id", "slug", name="uq_skill_domain_slug"),)


class SkillEdge(Base):
    __tablename__ = "skill_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    domain_id: Mapped[str] = mapped_column(ForeignKey("domain_packs.id", ondelete="CASCADE"))
    prerequisite_skill_id: Mapped[str] = mapped_column(ForeignKey("skill_nodes.id", ondelete="CASCADE"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skill_nodes.id", ondelete="CASCADE"))
    relation_type: Mapped[str] = mapped_column(String(40), default="prerequisite")

    __table_args__ = (
        UniqueConstraint(
            "prerequisite_skill_id",
            "skill_id",
            "relation_type",
            name="uq_skill_edge_relation",
        ),
    )


class LearnerSkillState(Base):
    __tablename__ = "learner_skill_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(120), index=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skill_nodes.id", ondelete="CASCADE"))
    mastery: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.1)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    skill: Mapped[SkillNode] = relationship()

    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_user_skill_state"),)


class LearningSession(Base):
    __tablename__ = "learning_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(120), index=True)
    domain_id: Mapped[str | None] = mapped_column(ForeignKey("domain_packs.id"), nullable=True)
    skill_id: Mapped[str | None] = mapped_column(ForeignKey("skill_nodes.id"), nullable=True)
    mode: Mapped[str] = mapped_column(String(40), default="learn")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=5)
    goal: Mapped[str] = mapped_column(Text, default="")
    reflection: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MasteryEvidence(Base):
    __tablename__ = "mastery_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(120), index=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skill_nodes.id", ondelete="CASCADE"))
    session_id: Mapped[str | None] = mapped_column(ForeignKey("learning_sessions.id"), nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(40))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_delta: Mapped[float] = mapped_column(Float, default=0.0)
    mastery_delta: Mapped[float] = mapped_column(Float, default=0.0)
    prompt: Mapped[str] = mapped_column(Text, default="")
    response: Mapped[str] = mapped_column(Text, default="")
    feedback: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    skill: Mapped[SkillNode] = relationship()


class TutorMessage(Base):
    __tablename__ = "tutor_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(120), index=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("learning_sessions.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(40), default="mock")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

