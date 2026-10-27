"""Use UUID4 user IDs as the primary key.

Revision ID: c7e41a0b926d
Revises: 8a4b2d6e901c
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.engine.interfaces import ReflectedForeignKeyConstraint

from alembic import op

revision: str = "c7e41a0b926d"
down_revision: str | None = "8a4b2d6e901c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _replace_primary_key(columns: list[str], *, drop_computing_id_unique: bool = False) -> None:
    # Foreign keys depend on a particular constraint, so rebind them when
    # replacing the primary key even though computing_id remains unique.
    inspector = sa.inspect(op.get_bind())
    references: list[tuple[str, ReflectedForeignKeyConstraint]] = [
        (table, foreign_key)
        for table in inspector.get_table_names()
        for foreign_key in inspector.get_foreign_keys(table)
        if foreign_key["referred_table"] == "site_user"
    ]
    for table, foreign_key in references:
        name = foreign_key["name"]
        if name is None:
            raise ValueError(f"Cannot replace an unnamed foreign key on {table}")
        op.drop_constraint(op.f(name), table, type_="foreignkey")
    op.drop_constraint(op.f("pk_site_user"), "site_user", type_="primary")
    op.create_primary_key(op.f("pk_site_user"), "site_user", columns)
    if drop_computing_id_unique:
        op.drop_constraint(op.f("uq_site_user_computing_id"), "site_user", type_="unique")
    for table, foreign_key in references:
        name = foreign_key["name"]
        if name is None:
            raise ValueError(f"Cannot replace an unnamed foreign key on {table}")
        op.create_foreign_key(
            op.f(name),
            table,
            "site_user",
            foreign_key["constrained_columns"],
            foreign_key["referred_columns"],
            **foreign_key.get("options", {}),
        )


def upgrade() -> None:
    op.add_column("site_user", sa.Column("uid", sa.Uuid(), nullable=True))
    users = sa.table("site_user", sa.column("computing_id", sa.String()), sa.column("uid", sa.Uuid()))
    connection = op.get_bind()
    for computing_id in connection.execute(sa.select(users.c.computing_id)).scalars():
        connection.execute(users.update().where(users.c.computing_id == computing_id).values(uid=uuid4()))
    op.alter_column("site_user", "uid", existing_type=sa.Uuid(), nullable=False)
    op.create_unique_constraint(op.f("uq_site_user_computing_id"), "site_user", ["computing_id"])
    _replace_primary_key(["uid"])
    op.alter_column("site_user", "computing_id", existing_type=sa.String(16), nullable=True)


def downgrade() -> None:
    op.alter_column("site_user", "computing_id", existing_type=sa.String(16), nullable=False)
    _replace_primary_key(["computing_id"], drop_computing_id_unique=True)
    op.drop_column("site_user", "uid")
