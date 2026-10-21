from dataclasses import dataclass
from datetime import datetime

from daily_trends_py.contexts.cms.users.domain.errors import InvalidAccessToken
from daily_trends_py.contexts.cms.users.domain.user import User
from daily_trends_py.contexts.cms.users.domain.user_repository import UserRepository
from daily_trends_py.contexts.cms.users.domain.verified_access_token import VerifiedAccessToken


@dataclass(frozen=True)
class AdminSession:
    user: User
    token_expires_at: datetime


class AdminSessionFinder:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def execute(self, token: VerifiedAccessToken) -> AdminSession:
        user = await self._repository.find_by_id(token.user_id)
        # A deleted user's token is still signed and unexpired; the client treats both the same.
        if user is None:
            raise InvalidAccessToken()
        return AdminSession(user=user, token_expires_at=token.expires_at)
