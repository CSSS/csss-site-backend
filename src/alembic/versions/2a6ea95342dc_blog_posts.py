"""blog_posts

Revision ID: 2a6ea95342dc
Revises: 43f71e4bd6fc
Create Date: 2024-08-31 03:06:11.516362

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a6ea95342dc"
down_revision: str | None = "166f3772fce7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("blog_posts",
        sa.Column("title", sa.String(length=128), primary_key=True, nullable=False),
        sa.Column("computing_id", sa.String(length=32), sa.ForeignKey("officer_info.computing_id"), nullable=False),
        sa.Column("date_created", sa.DateTime(), nullable=False),
        sa.Column("last_edited", sa.DateTime(), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("post_tags", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("blog_posts")
