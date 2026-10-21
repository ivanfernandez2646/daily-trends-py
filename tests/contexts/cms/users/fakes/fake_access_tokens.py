from daily_trends_py.contexts.cms.users.domain.access_token import AccessToken
from daily_trends_py.contexts.cms.users.domain.errors import InvalidAccessToken
from daily_trends_py.contexts.cms.users.domain.value_objects import UserId

PREFIX = "token-for:"


class FakeAccessTokens:
    """Issues `token-for:<user id>` and verifies only tokens shaped like that."""

    def __init__(self, expires_in_seconds: int = 3600) -> None:
        self._expires_in_seconds = expires_in_seconds
        self.issued_for: list[UserId] = []

    def issue(self, user_id: UserId) -> AccessToken:
        self.issued_for.append(user_id)
        return AccessToken(f"{PREFIX}{user_id.value}", self._expires_in_seconds)

    def verify(self, token: str) -> UserId:
        if not token.startswith(PREFIX):
            raise InvalidAccessToken()
        return UserId(token.removeprefix(PREFIX))
