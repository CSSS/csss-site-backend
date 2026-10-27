"""Separate internal event IDs from public ULIDs.

Revision ID: 8a4b2d6e901c
Revises: f06f13097539
"""

from collections.abc import Sequence

import sqlalchemy as sa
from ulid import ULID

from alembic import op

revision: str = "8a4b2d6e901c"
down_revision: str | None = "f06f13097539"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("event_info", "eid", new_column_name="id", existing_type=sa.Integer())
    op.add_column("event_info", sa.Column("eid", sa.String(26), nullable=True))

    events = sa.table("event_info", sa.column("id", sa.Integer()), sa.column("eid", sa.String(26)))
    connection = op.get_bind()
    for event_id in connection.execute(sa.select(events.c.id)).scalars():
        connection.execute(events.update().where(events.c.id == event_id).values(eid=str(ULID())))

    op.alter_column("event_info", "eid", existing_type=sa.String(26), nullable=False)
    op.create_unique_constraint(op.f("uq_event_info_eid"), "event_info", ["eid"])


def downgrade() -> None:
    op.drop_constraint(op.f("uq_event_info_eid"), "event_info", type_="unique")
    op.drop_column("event_info", "eid")
    op.alter_column("event_info", "id", new_column_name="eid", existing_type=sa.Integer())
