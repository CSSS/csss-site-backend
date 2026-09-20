import pytest

from auth.constants import UserRole
from utils.permissions import role_satisfies

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("assigned_role", list(UserRole))
def test__only_access_role_satisfies_access(assigned_role: UserRole):
    assert role_satisfies(assigned_role, UserRole.ACCESS) is (assigned_role is UserRole.ACCESS)


@pytest.mark.parametrize("required_role", list(UserRole))
def test__admin_satisfies_every_role_except_access(required_role: UserRole):
    assert role_satisfies(UserRole.ADMIN, required_role) is (required_role is not UserRole.ACCESS)
