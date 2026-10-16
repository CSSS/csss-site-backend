from pydantic import BaseModel, Field


class LoginBodyParams(BaseModel):
    service: str = Field(description="Service URL used for SFU's CAS system")
    ticket: str = Field(description="Ticket return from SFU's CAS system")
