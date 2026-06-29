from datetime import date

from pydantic import BaseModel, ConfigDict, Field, computed_field

from utils import is_active_term


class HonoraryMemberCreate(BaseModel):
    name: str = Field(..., max_length=128)
    start_date: date
    end_date: date | None = None


class HonoraryMember(HonoraryMemberCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int

    @computed_field
    @property
    def is_active(self) -> bool:
        return is_active_term(start_date=self.start_date, end_date=self.end_date)


class HonoraryMemberUpdate(BaseModel):
    name: str | None = Field(None, max_length=128)
    start_date: date | None = None
    end_date: date | None = None
