from pydantic import BaseModel


class DetailModel(BaseModel):
    detail: str


class MessageModel(BaseModel):
    message: str
