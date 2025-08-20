"""elections

Revision ID: 46d14891e1a9
Revises: 243190df5588
Create Date: 2025-08-19 21:58:08.035067

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "46d14891e1a9"
down_revision: str | None = "243190df5588"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
