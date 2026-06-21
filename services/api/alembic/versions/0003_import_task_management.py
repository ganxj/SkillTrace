"""import task management checkpoints

Revision ID: 0003_import_task_management
Revises: 0002_content_imports_and_lessons
Create Date: 2026-06-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0003_import_task_management"
down_revision: str | None = "0002_content_imports_and_lessons"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("content_imports", sa.Column("file_sha256", sa.String(length=64), nullable=False, server_default=""))
    op.add_column("content_imports", sa.Column("segment_packs_json", sa.Text(), nullable=False, server_default="[]"))
    op.add_column("content_imports", sa.Column("control_requested", sa.String(length=40), nullable=False, server_default=""))
    op.create_index(op.f("ix_content_imports_file_sha256"), "content_imports", ["file_sha256"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_content_imports_file_sha256"), table_name="content_imports")
    op.drop_column("content_imports", "control_requested")
    op.drop_column("content_imports", "segment_packs_json")
    op.drop_column("content_imports", "file_sha256")
