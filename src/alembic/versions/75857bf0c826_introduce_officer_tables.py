"""introduce officer tables

Revision ID: 75857bf0c826
Revises: 0db2c57ce969
Create Date: 2024-06-03 06:36:40.642476

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "75857bf0c826"
down_revision: str | None = "0db2c57ce969"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # drop all existing user session data
    # TODO: combine all past migrations into this one
    op.drop_table("user_session")
    op.create_table(
        "user_session",
        sa.Column("session_id", sa.String(512), nullable=False, primary_key=True),
        sa.Column("issue_time", sa.DateTime, nullable=False),
        sa.Column("computing_id", sa.String(32), nullable=False),
    )
    op.create_unique_constraint("unique__user_session__session_id", "user_session", ["session_id"])

    # drop all existing site user data
    # TODO: combine all past migrations into this one
    op.drop_table("site_user")
    op.create_table(
        "site_user",
        sa.Column("computing_id", sa.String(32), nullable=False, primary_key=True),
    )
    op.create_foreign_key(
        "fk__site_user__user_session__computing_id", "site_user", "user_session", ["computing_id"], ["computing_id"]
    )

    op.create_table(
        "officer_info",
        sa.Column("is_filled_in", sa.Boolean(), nullable=False),
        sa.Column("legal_name", sa.String(length=128), nullable=False),
        sa.Column("discord_id", sa.String(length=18), nullable=True),
        sa.Column("discord_name", sa.String(length=32), nullable=True),
        sa.Column("discord_nickname", sa.String(length=32), nullable=True),
        sa.Column("computing_id", sa.String(length=32), nullable=False),
        sa.Column("phone_number", sa.String(length=24), nullable=True),
        sa.Column("github_username", sa.String(length=39), nullable=True),
        sa.Column("google_drive_email", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["computing_id"], ["site_user.computing_id"], name="fk__officer_info__site_user__computing_id"
        ),
        sa.PrimaryKeyConstraint("computing_id", name="pk__officer_info__computing_id"),
    )
    op.create_table(
        "officer_term",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("computing_id", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_complete", sa.Boolean(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["computing_id"],
            ["site_user.computing_id"],
            # naming convention is "fk__<current class>__<target class>__<column name>"
            name="fk__officer_term__site_user__computing_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk__officer_term__id"),
        sa.UniqueConstraint("computing_id", name="unique__officer_term__computing_id"),
    )


def downgrade() -> None:
    op.drop_table("officer_term")
    op.drop_table("officer_info")

    op.drop_table("site_user")
    op.create_table(
        "site_user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("computing_id", sa.String(32), nullable=False),
    )

    op.drop_table("user_session")
    op.create_table(
        "user_session",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("issue_time", sa.DateTime, nullable=False),
        sa.Column("session_id", sa.String(512), nullable=False),
        sa.Column("computing_id", sa.String(32), nullable=False),
    )
