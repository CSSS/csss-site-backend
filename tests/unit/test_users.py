from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import users.crud
from auth.constants import UserRole
from auth.tables import SiteUserDB, SiteUserRoleDB
from users.models import SiteUserUpdate
from users.urls import update_site_user_roles

pytestmark = pytest.mark.unit


def make_user(computing_id: str, roles: set[UserRole]) -> SiteUserDB:
    return SiteUserDB(
        computing_id=computing_id,
        roles=[SiteUserRoleDB(computing_id=computing_id, role=role) for role in roles],
    )


async def test__update_site_user_roles_replaces_role_set(monkeypatch: pytest.MonkeyPatch):
    computing_id = "target"
    admin_id = "admin"
    user = make_user(computing_id, {UserRole.USER, UserRole.EXEC})
    desired_roles = {UserRole.EXEC, UserRole.ADMIN}

    db_session = AsyncMock(spec=AsyncSession)

    async def refresh_user(instance: SiteUserDB, *, attribute_names: list[str]):
        assert instance is user
        assert "roles" in attribute_names
        instance.roles = [
            SiteUserRoleDB(computing_id=computing_id, role=role, added_by=admin_id) for role in desired_roles
        ]

    db_session.refresh.side_effect = refresh_user

    get_user = AsyncMock(return_value=user)
    delete_roles = AsyncMock()
    create_roles = Mock()
    monkeypatch.setattr(users.crud, "get_user_for_role_update", get_user)
    monkeypatch.setattr(users.crud, "delete_user_roles", delete_roles)
    monkeypatch.setattr(users.crud, "create_user_roles", create_roles)

    result = await update_site_user_roles(
        db_session=db_session,
        admin_id=admin_id,
        computing_id=computing_id,
        body=SiteUserUpdate(roles=desired_roles),
    )

    delete_roles.assert_awaited_once_with(db_session, computing_id, {UserRole.USER})
    created_assignments = create_roles.call_args.args[1]
    assert {assignment.role for assignment in created_assignments} == {UserRole.ADMIN}
    assert all(assignment.added_by == admin_id for assignment in created_assignments)
    assert set(result.roles) == desired_roles
    db_session.flush.assert_awaited_once()
    db_session.commit.assert_awaited_once()
    db_session.rollback.assert_not_awaited()


async def test__update_site_user_roles_returns_not_found(monkeypatch: pytest.MonkeyPatch):
    db_session = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(users.crud, "get_user_for_role_update", AsyncMock(return_value=None))

    with pytest.raises(HTTPException) as exc_info:
        await update_site_user_roles(
            db_session=db_session,
            admin_id="admin",
            computing_id="missing",
            body=SiteUserUpdate(roles=set()),
        )

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    db_session.commit.assert_not_awaited()
