"""create election tables

Revision ID: 243190df5588
Revises: 43f71e4bd6fc
Create Date: 2024-08-10 08:32:54.037614

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "243190df5588"
down_revision: str | None = "2a6ea95342dc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "election",
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=64), default="general_election"),
        sa.Column("datetime_start_nominations", sa.DateTime(), nullable=False),
        sa.Column("datetime_start_voting", sa.DateTime(), nullable=False),
        sa.Column("datetime_end_voting", sa.DateTime(), nullable=False),
        sa.Column("survey_link", sa.String(length=300), nullable=True),
        sa.PrimaryKeyConstraint("slug")
    )
    op.create_table(
        "election_nominee",
        sa.Column("computing_id", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=64), nullable=False),
        sa.Column("facebook", sa.String(length=128), nullable=True),
        sa.Column("instagram", sa.String(length=128), nullable=True),
        sa.Column("email", sa.String(length=64), nullable=True),
        sa.Column("discord", sa.String(length=32), nullable=True),
        sa.Column("discord_id", sa.String(length=32), nullable=True),
        sa.Column("discord_username", sa.String(length=32), nullable=True),
        sa.PrimaryKeyConstraint("computing_id")
    )
    op.create_table(
        "nominee_application",
        sa.Column("computing_id", sa.String(length=32), nullable=False),
        sa.Column("nominee_election", sa.String(length=32), nullable=False),
        sa.Column("speech", sa.Text(), nullable=True),
        sa.Column("position", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["computing_id"], ["election_nominee.computing_id"]),
        sa.ForeignKeyConstraint(["nominee_election"], ["election.slug"]),
        sa.PrimaryKeyConstraint("computing_id", "nominee_election")
    )


def downgrade() -> None:
    op.drop_table("nominee_application")
    op.drop_table("election_nominee")
    op.drop_table("election")
