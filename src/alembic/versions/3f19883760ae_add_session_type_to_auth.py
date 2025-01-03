"""add session_type to auth

Revision ID: 3f19883760ae
Revises: 2a6ea95342dc
Create Date: 2025-01-03 00:16:50.579541

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f19883760ae"
down_revision: str | None = "2a6ea95342dc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_session", sa.Column("session_type", sa.String(48), nullable=False))

def downgrade() -> None:
    op.drop_column("user_session", "session_type")
