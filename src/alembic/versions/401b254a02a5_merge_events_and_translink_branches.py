"""Merge events and translink branches

Revision ID: 401b254a02a5
Revises: 42f855bec532, c1a70c8cfd64
Create Date: 2026-06-07 12:25:14.294686

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '401b254a02a5'
down_revision: Union[str, None] = ('42f855bec532', 'c1a70c8cfd64')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
