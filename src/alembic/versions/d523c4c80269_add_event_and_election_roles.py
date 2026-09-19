"""add event and election roles

Revision ID: d523c4c80269
Revises: b793b71fff3e
Create Date: 2026-09-19 14:44:06.114916

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd523c4c80269'
down_revision: Union[str, None] = 'b793b71fff3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    constraint = op.f('ck_site_user_role_role_valid')

    op.drop_constraint(constraint, 'site_user_role', type_='check')
    op.alter_column('site_user_role', 'role',
        existing_type=sa.String(length=5),
        type_=sa.String(length=8),
        existing_nullable=False
    )
    op.create_check_constraint(
        constraint,
        'site_user_role',
        "role IN ('admin', 'exec', 'user', 'event', 'election')",
    )


def downgrade() -> None:
    constraint = op.f('ck_site_user_role_role_valid')

    op.drop_constraint(constraint, 'site_user_role', type_='check')
    op.alter_column('site_user_role', 'role',
        existing_type=sa.String(length=8),
        type_=sa.String(length=5),
        existing_nullable=False
    )
    op.create_check_constraint(
        constraint,
        'site_user_role',
        "role IN ('admin', 'exec', 'user')",
    )
