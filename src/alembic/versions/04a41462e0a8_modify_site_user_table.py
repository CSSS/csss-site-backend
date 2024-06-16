"""modify site user table

Revision ID: 04a41462e0a8
Revises: 0db2c57ce969
Create Date: 2024-06-16 11:27:51.273966

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04a41462e0a8'
down_revision: Union[str, None] = '0db2c57ce969'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # add first_logged_in, last_logged_in columns
    op.add_column('site_user', sa.Column('first_logged_in', sa.DateTime, nullable=False, default=datetime(2024, 6, 16)))
    op.add_column('site_user', sa.Column('last_logged_in', sa.DateTime, nullable=False, default=datetime(2024, 6, 16)))


def downgrade() -> None:
    # drop first_logged_in, last_logged_in columns
    op.drop_column('site_user', 'first_logged_in')
    op.drop_column('site_user', 'last_logged_in')
