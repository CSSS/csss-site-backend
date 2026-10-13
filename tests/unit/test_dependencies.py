from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import auth.crud
from auth.constants import UserRole
from auth.crud import SessionUser
from dependencies import (
    PERMISSION_DEPENDENCIES,
    authenticated_user,
    authenticated_user_id,
    optional_session_user,
    optional_user_id,
    perm_exec,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("computing_id", ["testuser", None])
def test__identity_dependencies_return_uid(computing_id: str | None):
    user = SessionUser(computing_id, uuid4(), frozenset({UserRole.ACCESS}))
    assert authenticated_user(user) is user
    assert optional_user_id(user) == authenticated_user_id(user) == user.uid
    assert isinstance(authenticated_user_id(user), UUID)
    for dependency in PERMISSION_DEPENDENCIES:
        assert dependency(user) == user.uid


def test__missing_identity_is_optional_or_unauthorized():
    assert optional_user_id(None) is None
    with pytest.raises(HTTPException) as error:
        authenticated_user(None)
    assert error.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize("dependency", PERMISSION_DEPENDENCIES)
def test__roles_deny_users_without_permission(dependency):
    user = SessionUser(None, uuid4(), frozenset())
    with pytest.raises(HTTPException) as error:
        dependency(user)
    assert error.value.status_code == status.HTTP_403_FORBIDDEN


def test__role_dependency_accepts_inherited_permission():
    user = SessionUser(None, uuid4(), frozenset({UserRole.ADMIN}))
    assert perm_exec(user) == user.uid


async def test__missing_session_does_not_query_database(monkeypatch: pytest.MonkeyPatch):
    lookup = AsyncMock()
    monkeypatch.setattr(auth.crud, "get_session_user", lookup)
    assert await optional_session_user(AsyncMock(spec=AsyncSession), None) is None
    lookup.assert_not_awaited()


async def test__invalid_session_has_no_identity(monkeypatch: pytest.MonkeyPatch):
    lookup = AsyncMock(return_value=None)
    monkeypatch.setattr(auth.crud, "get_session_user", lookup)
    db_session = AsyncMock(spec=AsyncSession)
    assert await optional_session_user(db_session, "invalid") is None
    lookup.assert_awaited_once_with(db_session, "invalid")
