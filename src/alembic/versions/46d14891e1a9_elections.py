"""elections

Revision ID: 46d14891e1a9
Revises: 243190df5588
Create Date: 2025-08-19 21:58:08.035067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46d14891e1a9'
down_revision: Union[str, None] = '243190df5588'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
