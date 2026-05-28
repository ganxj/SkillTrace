"""content imports and generated lessons

Revision ID: 0002_content_imports_and_lessons
Revises: 0001_initial_learning_os
Create Date: 2026-05-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002_content_imports_and_lessons"
down_revision: str | None = "0001_initial_learning_os"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("skill_nodes", sa.Column("lesson_explain", sa.Text(), nullable=False, server_default=""))
    op.add_column("skill_nodes", sa.Column("key_points_json", sa.Text(), nullable=False, server_default="[]"))
    op.add_column("skill_nodes", sa.Column("questions_json", sa.Text(), nullable=False, server_default="[]"))

    op.create_table(
        "content_imports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=260), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("generated_json", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("domain_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["domain_id"], ["domain_packs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("content_imports")
    op.drop_column("skill_nodes", "questions_json")
    op.drop_column("skill_nodes", "key_points_json")
    op.drop_column("skill_nodes", "lesson_explain")
