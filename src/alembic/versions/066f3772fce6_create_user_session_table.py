"""create user session table

Revision ID: 066f3772fce6
Revises: 
Create Date: 2024-02-23 00:58:50.320796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '066f3772fce6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_session',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('issue_time', sa.DateTime, nullable=False),
        sa.Column('session_id', sa.String(512), nullable=False),
        sa.Column('computing_id', sa.String(32), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('user_session')
