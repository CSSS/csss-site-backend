"""empty message

Revision ID: 43f71e4bd6fc
Revises: 04a41462e0a8, 75857bf0c826
Create Date: 2024-08-07 07:42:44.774426

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "43f71e4bd6fc"
down_revision: str | None = ("04a41462e0a8", "75857bf0c826")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
