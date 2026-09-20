import pytest
from pydantic import ValidationError

from officers.models import OfficerInfoUpdate


def test__officer_info_update_allows_omitted_legal_name():
    update = OfficerInfoUpdate(phone_number="123")
    assert update.model_dump(exclude_unset=True) == {"phone_number": "123"}


def test__officer_info_update_rejects_null_legal_name():
    with pytest.raises(ValidationError):
        OfficerInfoUpdate(legal_name=None)
