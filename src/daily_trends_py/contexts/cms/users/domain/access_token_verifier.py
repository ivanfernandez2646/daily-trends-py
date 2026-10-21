from typing import Protocol

from daily_trends_py.contexts.cms.users.domain.value_objects import UserId


class AccessTokenVerifier(Protocol):
    def verify(self, token: str) -> UserId:
        """The user the token was issued for; raises `InvalidAccessToken` otherwise."""
        ...
