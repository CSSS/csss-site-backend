from pydantic import BaseModel


class SuccessFailModel(BaseModel):
    success: bool

class DetailModel(BaseModel):
    detail: str

class MessageModel(BaseModel):
    message: str
