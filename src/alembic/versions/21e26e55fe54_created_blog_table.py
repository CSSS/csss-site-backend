"""created blog table??

Revision ID: 21e26e55fe54
Revises: 43f71e4bd6fc
Create Date: 2024-08-08 15:19:53.671327

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "21e26e55fe54"
down_revision: str | None = "43f71e4bd6fc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
