from pydantic import BaseModel, ConfigDict


class CounterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    good: int
    evil: int
