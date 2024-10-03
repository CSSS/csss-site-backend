"""create user session table

Revision ID: 166f3772fce7
Revises:
Create Date: 2024-02-23 00:58:50.320796

"""

from collections.abc import Sequence
from datetime import datetime
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "166f3772fce7"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "site_user",
        sa.Column("computing_id", sa.String(32), primary_key=True),
        sa.Column("first_logged_in", sa.DateTime, nullable=False, default=datetime(2024, 6, 16)),
        sa.Column("last_logged_in", sa.DateTime, nullable=False, default=datetime(2024, 6, 16)),
    )
    op.create_table(
        "user_session",
        # NOTE: order is important; site_user must be created first!
        sa.Column("computing_id", sa.String(32), sa.ForeignKey("site_user.computing_id"), primary_key=True),
        sa.Column("issue_time", sa.DateTime, nullable=False),
        sa.Column("session_id", sa.String(512), nullable=False, unique=True),
    )

    op.create_table(
        "officer_term",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("computing_id", sa.String(length=32), sa.ForeignKey("site_user.computing_id"), nullable=False),
        sa.Column("position", sa.String(length=128), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("nickname", sa.String(length=128), nullable=True),
        sa.Column("favourite_course_0", sa.String(length=32), nullable=True),
        sa.Column("favourite_course_1", sa.String(length=32), nullable=True),
        sa.Column("favourite_pl_0", sa.String(length=32), nullable=True),
        sa.Column("favourite_pl_1", sa.String(length=32), nullable=True),
        sa.Column("biography", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.Text(), nullable=True),
    )
    op.create_table(
        "officer_info",
        sa.Column("legal_name", sa.String(length=128), nullable=False),
        sa.Column("discord_id", sa.String(length=18), nullable=True),
        sa.Column("discord_name", sa.String(length=32), nullable=True),
        sa.Column("discord_nickname", sa.String(length=32), nullable=True),
        sa.Column("computing_id", sa.String(length=32), sa.ForeignKey("user_session.computing_id"), primary_key=True),
        sa.Column("phone_number", sa.String(length=24), nullable=True),
        sa.Column("github_username", sa.String(length=39), nullable=True),
        sa.Column("google_drive_email", sa.String(length=256), nullable=True),
    )

def downgrade() -> None:
    op.drop_table("officer_info")
    op.drop_table("officer_term")

    op.drop_table("user_session")
    op.drop_table("site_user")
