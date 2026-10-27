"""Reference user UUIDs from sessions and role assignments.

Revision ID: d9a62b4f013e
Revises: c7e41a0b926d
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d9a62b4f013e"
down_revision: str | None = "c7e41a0b926d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    users = sa.table("site_user", sa.column("computing_id", sa.String(16)), sa.column("uid", sa.Uuid()))
    for table in ("user_session", "site_user_role"):
        op.add_column(table, sa.Column("uid", sa.Uuid(), nullable=True))
        target = sa.table(table, sa.column("computing_id", sa.String(16)), sa.column("uid", sa.Uuid()))
        op.execute(target.update().where(target.c.computing_id == users.c.computing_id).values(uid=users.c.uid))
        op.alter_column(table, "uid", existing_type=sa.Uuid(), nullable=False)
        op.drop_constraint(op.f(f"fk_{table}_computing_id_site_user"), table, type_="foreignkey")
        op.drop_constraint(op.f(f"ck_{table}_computing_id_format"), table, type_="check")

    op.add_column("site_user_role", sa.Column("added_by_uid", sa.Uuid(), nullable=True))
    roles = sa.table("site_user_role", sa.column("added_by", sa.String(16)), sa.column("added_by_uid", sa.Uuid()))
    op.execute(roles.update().where(roles.c.added_by == users.c.computing_id).values(added_by_uid=users.c.uid))
    op.drop_constraint(op.f("fk_site_user_role_added_by_site_user"), "site_user_role", type_="foreignkey")
    op.drop_constraint(op.f("ck_site_user_role_added_by_format"), "site_user_role", type_="check")
    op.drop_column("site_user_role", "added_by")
    op.alter_column("site_user_role", "added_by_uid", new_column_name="added_by", existing_type=sa.Uuid())

    op.drop_constraint(op.f("pk_site_user_role"), "site_user_role", type_="primary")
    op.drop_index(op.f("ix_user_session_computing_id"), table_name="user_session")
    for table in ("user_session", "site_user_role"):
        op.drop_column(table, "computing_id")
        op.create_foreign_key(op.f(f"fk_{table}_uid_site_user"), table, "site_user", ["uid"], ["uid"])
    op.create_primary_key(op.f("pk_site_user_role"), "site_user_role", ["uid", "role"])
    op.create_index(op.f("ix_user_session_uid"), "user_session", ["uid"])
    op.create_foreign_key(
        op.f("fk_site_user_role_added_by_site_user"),
        "site_user_role",
        "site_user",
        ["added_by"],
        ["uid"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    users = sa.table("site_user", sa.column("computing_id", sa.String(16)), sa.column("uid", sa.Uuid()))
    for table in ("user_session", "site_user_role"):
        op.add_column(table, sa.Column("computing_id", sa.String(16), nullable=True))
        target = sa.table(table, sa.column("computing_id", sa.String(16)), sa.column("uid", sa.Uuid()))
        op.execute(target.update().where(target.c.uid == users.c.uid).values(computing_id=users.c.computing_id))
        op.alter_column(table, "computing_id", existing_type=sa.String(16), nullable=False)
        op.drop_constraint(op.f(f"fk_{table}_uid_site_user"), table, type_="foreignkey")

    op.add_column("site_user_role", sa.Column("added_by_computing_id", sa.String(16), nullable=True))
    roles = sa.table(
        "site_user_role",
        sa.column("added_by", sa.Uuid()),
        sa.column("added_by_computing_id", sa.String(16)),
    )
    op.execute(roles.update().where(roles.c.added_by == users.c.uid).values(added_by_computing_id=users.c.computing_id))
    op.drop_constraint(op.f("fk_site_user_role_added_by_site_user"), "site_user_role", type_="foreignkey")
    op.drop_column("site_user_role", "added_by")
    op.alter_column(
        "site_user_role",
        "added_by_computing_id",
        new_column_name="added_by",
        existing_type=sa.String(16),
    )

    op.drop_constraint(op.f("pk_site_user_role"), "site_user_role", type_="primary")
    op.drop_index(op.f("ix_user_session_uid"), table_name="user_session")
    for table in ("user_session", "site_user_role"):
        op.drop_column(table, "uid")
        op.create_foreign_key(
            op.f(f"fk_{table}_computing_id_site_user"),
            table,
            "site_user",
            ["computing_id"],
            ["computing_id"],
        )
        op.create_check_constraint(
            op.f(f"ck_{table}_computing_id_format"),
            table,
            "computing_id ~ '^[a-z0-9]+$' AND computing_id = lower(computing_id)",
        )
    op.create_primary_key(op.f("pk_site_user_role"), "site_user_role", ["computing_id", "role"])
    op.create_index(op.f("ix_user_session_computing_id"), "user_session", ["computing_id"])
    op.create_foreign_key(
        op.f("fk_site_user_role_added_by_site_user"),
        "site_user_role",
        "site_user",
        ["added_by"],
        ["computing_id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        op.f("ck_site_user_role_added_by_format"),
        "site_user_role",
        "added_by IS NULL OR added_by ~ '^[a-z0-9]+$'",
    )
