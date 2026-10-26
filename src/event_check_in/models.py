from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


class EventCheckInCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=64, pattern=r"\S")
    enabled: bool = False
    opens_at: AwareDatetime | None = None
    closes_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.opens_at is not None and self.closes_at is not None:
            if self.closes_at <= self.opens_at:
                raise ValueError("closes_at must be later than opens_at")
        return self


# IDs and audit timestamps are returned to clients but are not writable inputs
class EventCheckIn(EventCheckInCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: AwareDatetime
    updated_at: AwareDatetime


# PATCH keeps omitted fields unchanged; null can clear opens_at or closes_at
class EventCheckInUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=64, pattern=r"\S")
    enabled: bool | None = None
    opens_at: AwareDatetime | None = None
    closes_at: AwareDatetime | None = None

    # Name and enabled can be omitted from PATCH, but must have a value when provided
    @field_validator("name", "enabled")
    @classmethod
    def reject_null_values(cls, value: object) -> object:
        if value is None:
            raise ValueError("This field cannot be null")
        return value
