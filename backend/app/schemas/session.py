from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    passcode: str


class SessionResponse(BaseModel):
    authenticated: Literal[True]
    expires_at: datetime = Field(alias="expiresAt")

    model_config = {"populate_by_name": True}
