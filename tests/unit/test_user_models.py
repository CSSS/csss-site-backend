from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.constants import UserRole
from auth.tables import SiteUserDB, SiteUserRoleDB
from users.models import SiteUser, SiteUserCreate, SiteUserUpdate, UserInfo
from users.urls import create_site_user

pytestmark = pytest.mark.unit


@pytest.fixture
def user():
    uid = uuid4()
    return SiteUserDB(
        uid=uid,
        computing_id="example",
        first_name="Legal",
        last_name="Name",
        preferred_name="Display",
        first_logged_in=datetime.now(UTC),
        last_logged_in=datetime.now(UTC),
        roles=[SiteUserRoleDB(uid=uid, role=UserRole.EXEC)],
    )


def test_private_responses_include_names_and_only_admin_has_login_history(user):
    admin = SiteUser.model_validate(user).model_dump()
    account = UserInfo.model_validate(user).model_dump()
    for response in (admin, account):
        assert response["uid"] == user.uid
        assert response["computing_id"] == "example"
        assert response["first_name"] == "Legal"
        assert response["last_name"] == "Name"
        assert response["preferred_name"] == "Display"
        assert response["roles"] == [UserRole.EXEC]
    assert admin["first_logged_in"] == user.first_logged_in
    assert admin["last_logged_in"] == user.last_logged_in
    assert "first_logged_in" not in account
    assert "last_logged_in" not in account
    assert UserRole.USER in account["effective_roles"]


@pytest.mark.parametrize("model", [SiteUserCreate, SiteUserUpdate])
@pytest.mark.parametrize("field", ["first_name", "last_name", "preferred_name"])
def test_requests_enforce_database_name_length(model, field):
    values = {"computing_id": "example"} if model is SiteUserCreate else {}
    with pytest.raises(ValidationError):
        model.model_validate({**values, field: "x" * 65})
    assert getattr(model.model_validate({**values, field: "x" * 64}), field) == "x" * 64


def test_update_distinguishes_omitted_names_from_explicit_null():
    assert SiteUserUpdate().model_dump(exclude_unset=True) == {}  # pyright: ignore[reportCallIssue]
    assert SiteUserUpdate(first_name=None).model_dump(exclude_unset=True) == {"first_name": None}  # pyright: ignore[reportCallIssue]


async def test_create_persists_names_without_client_uid():
    session = AsyncMock(spec=AsyncSession)
    body = SiteUserCreate(computing_id="example", first_name="Legal", last_name="Name", preferred_name="Display")
    result = await create_site_user(session, uuid4(), body)
    saved_user = session.add.call_args.args[0]
    assert result.uid.version == 4
    for field in ("first_name", "last_name", "preferred_name"):
        assert getattr(saved_user, field) == getattr(body, field)
        assert getattr(result, field) == getattr(body, field)
    session.commit.assert_awaited_once()
