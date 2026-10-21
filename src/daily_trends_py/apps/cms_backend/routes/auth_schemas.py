from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict

from daily_trends_py.contexts.cms.users.application.find_session.admin_session_finder import (
    AdminSession,
)
from daily_trends_py.contexts.cms.users.domain.access_token import AccessToken


class LoginRequest(BaseModel):
    # Strict: a number or a list is never coerced into a string.
    model_config = ConfigDict(strict=True)

    email: str
    password: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int

    @classmethod
    def from_access_token(cls, token: AccessToken) -> Self:
        return cls(
            access_token=token.value, token_type="bearer", expires_in=token.expires_in_seconds
        )


class AdminSessionResponse(BaseModel):
    id: str
    email: str
    created_at: datetime
    token_expires_at: datetime

    @classmethod
    def from_admin_session(cls, session: AdminSession) -> Self:
        return cls(
            id=session.user.id.value,
            email=session.user.email.value,
            created_at=session.user.created_at.value,
            token_expires_at=session.token_expires_at,
        )
