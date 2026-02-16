from pydantic import BaseModel


class SuccessResponse(BaseModel):
    success: bool


class DetailModel(BaseModel):
    detail: str


class MessageModel(BaseModel):
    message: str
