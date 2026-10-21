from typing import Protocol

from daily_trends_py.contexts.cms.users.domain.verified_access_token import VerifiedAccessToken


class AccessTokenVerifier(Protocol):
    def verify(self, token: str) -> VerifiedAccessToken:
        """Who the token was issued for and its expiry; raises `InvalidAccessToken` otherwise."""
        ...
