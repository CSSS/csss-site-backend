from pydantic import BaseModel


class CounterResponse(BaseModel):
    good: int
    evil: int
