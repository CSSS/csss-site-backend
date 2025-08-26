from pydantic import BaseModel


class SuccessFailModel(BaseModel):
    success: bool
