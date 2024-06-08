"""add persistent user table

Revision ID: 0db2c57ce969
Revises: 066f3772fce6
Create Date: 2024-05-21 03:42:05.201901

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0db2c57ce969"
down_revision: str | None = "066f3772fce6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "site_user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("computing_id", sa.String(32), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("site_user")
