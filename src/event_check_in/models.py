from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from event_check_in.constants import EVENT_CHECK_IN_NAME_MAX_LEN


class EventCheckInCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=1,
        max_length=EVENT_CHECK_IN_NAME_MAX_LEN,
        pattern=r"\S",
        description="Name of the check-in configuration",
    )
    enabled: bool = Field(
        default=False,
        description="Whether this check-in configuration is enabled",
    )
    opens_at: AwareDatetime | None = Field(
        default=None,
        description="Opening time with timezone; null means no opening-time limit",
    )
    closes_at: AwareDatetime | None = Field(
        default=None,
        description="Closing time with timezone; null means no closing-time limit",
    )

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.opens_at is not None and self.closes_at is not None:
            if self.closes_at <= self.opens_at:
                raise ValueError("closes_at must be later than opens_at")
        return self


# IDs and audit timestamps are returned to clients but are not writable inputs
class EventCheckIn(EventCheckInCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Unique ID of the check-in configuration")
    created_at: AwareDatetime = Field(
        description="Time the check-in configuration was created",
    )
    updated_at: AwareDatetime = Field(
        description="Time the check-in configuration was last updated",
    )


# PATCH keeps omitted fields unchanged; null can clear opens_at or closes_at
class EventCheckInUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=EVENT_CHECK_IN_NAME_MAX_LEN,
        pattern=r"\S",
        description="Updated name. Omit to keep unchanged; null is not allowed",
    )
    enabled: bool | None = Field(
        default=None,
        description="Updated enabled status. Omit to keep unchanged; null is not allowed",
    )
    opens_at: AwareDatetime | None = Field(
        default=None,
        description="Opening time with timezone. Omit to keep unchanged; null clears the limit",
    )
    closes_at: AwareDatetime | None = Field(
        default=None,
        description="Closing time with timezone. Omit to keep unchanged; null clears the limit",
    )

    # Name and enabled can be omitted from PATCH, but must have a value when provided
    @field_validator("name", "enabled")
    @classmethod
    def reject_null_values(cls, value: object) -> object:
        if value is None:
            raise ValueError("This field cannot be null")
        return value
