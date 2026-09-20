import pytest

from auth.constants import UserRole
from auth.models import UserInfo

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("assigned_roles", "expected_roles"),
    [
        ([], []),
        ([UserRole.USER], [UserRole.USER]),
        ([UserRole.OFFICER], [UserRole.OFFICER, UserRole.USER]),
        ([UserRole.EXEC], [UserRole.EXEC, UserRole.OFFICER, UserRole.USER]),
        (
            [UserRole.ADMIN],
            [
                UserRole.ADMIN,
                UserRole.EXEC,
                UserRole.OFFICER,
                UserRole.USER,
                UserRole.EVENT,
                UserRole.ELECTION,
            ],
        ),
        ([UserRole.ACCESS], list(UserRole)),
        ([UserRole.EVENT], [UserRole.EVENT]),
        ([UserRole.ELECTION], [UserRole.ELECTION]),
        (
            [UserRole.EVENT, UserRole.EXEC, UserRole.USER],
            [UserRole.EXEC, UserRole.OFFICER, UserRole.USER, UserRole.EVENT],
        ),
    ],
)
def test__effective_roles_include_all_granted_permissions(
    assigned_roles: list[UserRole],
    expected_roles: list[UserRole],
):
    user = UserInfo(computing_id="test", roles=assigned_roles)

    assert user.effective_roles == expected_roles
