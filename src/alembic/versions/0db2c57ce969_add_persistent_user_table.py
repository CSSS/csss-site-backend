"""add persistent user table

Revision ID: 0db2c57ce969
Revises: 066f3772fce6
Create Date: 2024-05-21 03:42:05.201901

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0db2c57ce969"
down_revision: Union[str, None] = "066f3772fce6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "site_user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("computing_id", sa.String(32), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("site_user")
