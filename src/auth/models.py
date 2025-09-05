from pydantic import BaseModel, Field


class LoginBodyModel(BaseModel):
    service: str = Field(description="Service URL used for SFU's CAS system")
    ticket: str = Field(description="Ticket return from SFU's CAS system")
    redirect_url: str | None = Field(None, description="Optional redirect URL")
