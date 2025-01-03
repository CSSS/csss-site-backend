"""add exam bank tables

Revision ID: 2f1b67c68ba5
Revises: 3f19883760ae
Create Date: 2025-01-03 00:24:44.608869

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2f1b67c68ba5"
down_revision: str | None = "3f19883760ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "professor",
        sa.Column("professor_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("info_url", sa.String(128), nullable=False),
        sa.Column("computing_id", sa.String(32), sa.ForeignKey("user_session.computing_id"), nullable=True),
    )

    op.create_table(
        "course",
        sa.Column("course_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("course_faculty", sa.String(12), nullable=False),
        sa.Column("course_number", sa.String(12), nullable=False),
        sa.Column("course_name", sa.String(96), nullable=False),
    )

    op.create_table(
        "exam_metadata",
        sa.Column("exam_id", sa.Integer, primary_key=True),
        sa.Column("upload_date", sa.DateTime, nullable=False),
        sa.Column("exam_pdf_size", sa.Integer, nullable=False),

        sa.Column("author_id", sa.String(32), sa.ForeignKey("professor.professor_id"), nullable=False),
        sa.Column("author_confirmed", sa.Boolean, nullable=False),
        sa.Column("author_permission", sa.Boolean, nullable=False),

        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("course_id", sa.String(32), sa.ForeignKey("professor.professor_id"), nullable=True),
        sa.Column("title", sa.String(96), nullable=True),
        sa.Column("description", sa.Text, nullable=True),

        sa.Column("date_string", sa.String(10), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("exam_metadata")
    op.drop_table("professor")
    op.drop_table("course")
