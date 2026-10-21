from datetime import UTC, datetime

from daily_trends_py.contexts.cms.users.domain.access_token import AccessToken
from daily_trends_py.contexts.cms.users.domain.errors import InvalidAccessToken
from daily_trends_py.contexts.cms.users.domain.value_objects import UserId
from daily_trends_py.contexts.cms.users.domain.verified_access_token import VerifiedAccessToken

PREFIX = "token-for:"
EXPIRES_AT = datetime(2026, 10, 21, 18, 0, 0, tzinfo=UTC)


class FakeAccessTokens:
    """Issues `token-for:<user id>` and verifies only tokens shaped like that, all expiring at
    `expires_at`."""

    def __init__(self, expires_in_seconds: int = 3600, expires_at: datetime = EXPIRES_AT) -> None:
        self._expires_in_seconds = expires_in_seconds
        self._expires_at = expires_at
        self.issued_for: list[UserId] = []

    def issue(self, user_id: UserId) -> AccessToken:
        self.issued_for.append(user_id)
        return AccessToken(f"{PREFIX}{user_id.value}", self._expires_in_seconds)

    def verify(self, token: str) -> VerifiedAccessToken:
        if not token.startswith(PREFIX):
            raise InvalidAccessToken()
        return VerifiedAccessToken(UserId(token.removeprefix(PREFIX)), self._expires_at)
