from datetime import timedelta
from typing import Any

import jwt
from jwt.types import Options

from daily_trends_py.contexts.cms.shared.domain.clock import Clock
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.users.domain.access_token import AccessToken
from daily_trends_py.contexts.cms.users.domain.errors import InvalidAccessToken
from daily_trends_py.contexts.cms.users.domain.value_objects import UserId

_ALGORITHM = "HS256"
# PyJWT checks times against the system clock, so expiry is checked against `Clock` instead.
_DECODE_OPTIONS: Options = {
    "verify_exp": False,
    "verify_iat": False,
    "verify_nbf": False,
    "require": ["sub", "exp"],
}


class JwtAccessTokens:
    """HS256 tokens with `sub`, `iat` and `exp`, valid for `ttl` from the moment they are issued.

    Verification reads no storage: a token stays valid until it expires.
    """

    def __init__(self, secret_key: str, ttl: timedelta, clock: Clock) -> None:
        self._secret_key = secret_key
        self._ttl_seconds = int(ttl.total_seconds())
        self._clock = clock

    def issue(self, user_id: UserId) -> AccessToken:
        issued_at = int(self._clock.now().timestamp())
        claims: dict[str, object] = {
            "sub": user_id.value,
            "iat": issued_at,
            "exp": issued_at + self._ttl_seconds,
        }
        return AccessToken(_encode(claims, self._secret_key), self._ttl_seconds)

    def verify(self, token: str) -> UserId:
        try:
            claims = _decode(token, self._secret_key)
            # PyJWT already rejects an `exp` that is not a number.
            if self._clock.now().timestamp() >= claims["exp"]:
                raise InvalidAccessToken()
            return UserId(claims["sub"])
        except (jwt.InvalidTokenError, InvalidArgumentError) as error:
            raise InvalidAccessToken() from error


# PyJWT types its keys with `cryptography` classes, unknown without that optional package; only
# string keys are used here.
def _encode(claims: dict[str, object], key: str) -> str:
    return jwt.encode(claims, key, algorithm=_ALGORITHM)  # pyright: ignore[reportUnknownMemberType]


# `Any`: the decoded claims are JSON values only known at runtime.
def _decode(token: str, key: str) -> dict[str, Any]:
    return jwt.decode(  # pyright: ignore[reportUnknownMemberType]
        token, key, algorithms=[_ALGORITHM], options=_DECODE_OPTIONS
    )
