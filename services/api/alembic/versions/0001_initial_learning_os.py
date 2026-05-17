"""initial learning os schema

Revision ID: 0001_initial_learning_os
Revises:
Create Date: 2026-05-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_learning_os"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "domain_packs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_domain_packs_slug"), "domain_packs", ["slug"], unique=True)

    op.create_table(
        "skill_nodes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("domain_id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domain_packs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain_id", "slug", name="uq_skill_domain_slug"),
    )
    op.create_index(op.f("ix_skill_nodes_slug"), "skill_nodes", ["slug"], unique=False)

    op.create_table(
        "learning_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("domain_id", sa.String(length=36), nullable=True),
        sa.Column("skill_id", sa.String(length=36), nullable=True),
        sa.Column("mode", sa.String(length=40), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("reflection", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["domain_id"], ["domain_packs.id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skill_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_learning_sessions_user_id"), "learning_sessions", ["user_id"], unique=False
    )

    op.create_table(
        "skill_edges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("domain_id", sa.String(length=36), nullable=False),
        sa.Column("prerequisite_skill_id", sa.String(length=36), nullable=False),
        sa.Column("skill_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["domain_id"], ["domain_packs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["prerequisite_skill_id"], ["skill_nodes.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skill_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "prerequisite_skill_id", "skill_id", "relation_type", name="uq_skill_edge_relation"
        ),
    )

    op.create_table(
        "learner_skill_states",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("skill_id", sa.String(length=36), nullable=False),
        sa.Column("mastery", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("review_due_at", sa.DateTime(), nullable=True),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["skill_id"], ["skill_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "skill_id", name="uq_user_skill_state"),
    )
    op.create_index(
        op.f("ix_learner_skill_states_user_id"),
        "learner_skill_states",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "mastery_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("skill_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("evidence_type", sa.String(length=40), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence_delta", sa.Float(), nullable=False),
        sa.Column("mastery_delta", sa.Float(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skill_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mastery_evidence_user_id"), "mastery_evidence", ["user_id"], unique=False
    )

    op.create_table(
        "tutor_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tutor_messages_user_id"), "tutor_messages", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tutor_messages_user_id"), table_name="tutor_messages")
    op.drop_table("tutor_messages")
    op.drop_index(op.f("ix_mastery_evidence_user_id"), table_name="mastery_evidence")
    op.drop_table("mastery_evidence")
    op.drop_index(op.f("ix_learner_skill_states_user_id"), table_name="learner_skill_states")
    op.drop_table("learner_skill_states")
    op.drop_table("skill_edges")
    op.drop_index(op.f("ix_learning_sessions_user_id"), table_name="learning_sessions")
    op.drop_table("learning_sessions")
    op.drop_index(op.f("ix_skill_nodes_slug"), table_name="skill_nodes")
    op.drop_table("skill_nodes")
    op.drop_index(op.f("ix_domain_packs_slug"), table_name="domain_packs")
    op.drop_table("domain_packs")

