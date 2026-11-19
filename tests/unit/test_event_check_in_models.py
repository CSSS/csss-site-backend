import pytest
from pydantic import ValidationError

from event_check_in.models import EventCheckInCreate, EventCheckInUpdate

pytestmark = pytest.mark.unit


def test_create_defaults_to_disabled_without_time_limits():
    check_in = EventCheckInCreate(name="Main check-in")

    assert check_in.enabled is False
    assert check_in.opens_at is None
    assert check_in.closes_at is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": ""},
        {"name": "   "},
        {"name": "x" * 65},
        {"name": "Main", "opens_at": "2026-10-25T17:00:00"},
        {"name": "Main", "closes_at": "2026-10-25T18:00:00"},
    ],
)
def test_create_rejects_invalid_names_and_timezone_missing_dates(payload):
    with pytest.raises(ValidationError):
        EventCheckInCreate.model_validate(payload)


@pytest.mark.parametrize(
    "closes_at",
    [
        "2026-10-25T17:00:00-07:00",
        "2026-10-25T16:00:00-07:00",
        "2026-10-25T23:30:00Z",
    ],
)
def test_create_rejects_closing_at_or_before_opening(closes_at):
    with pytest.raises(
        ValidationError,
        match="closes_at must be later than opens_at",
    ):
        EventCheckInCreate.model_validate(
            {
                "name": "Main check-in",
                "opens_at": "2026-10-25T17:00:00-07:00",
                "closes_at": closes_at,
            }
        )


def test_update_distinguishes_omitted_fields_from_false_and_null():
    unchanged = EventCheckInUpdate()
    updated = EventCheckInUpdate(
        enabled=False,
        opens_at=None,
        closes_at=None,
    )

    assert unchanged.model_dump(exclude_unset=True) == {}
    assert updated.model_dump(exclude_unset=True) == {
        "enabled": False,
        "opens_at": None,
        "closes_at": None,
    }


@pytest.mark.parametrize("field", ["name", "enabled"])
def test_update_rejects_null_for_required_fields(field):
    with pytest.raises(ValidationError):
        EventCheckInUpdate.model_validate({field: None})
