import base64
import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from daily_trends_py.contexts.cms.users.domain.errors import InvalidAccessToken
from daily_trends_py.contexts.cms.users.infrastructure.tokens.jwt_access_tokens import (
    JwtAccessTokens,
)
from tests.contexts.cms.shared.fakes.fixed_clock import FixedClock
from tests.contexts.cms.users.domain.user_id_mother import UserIdMother

# 64 characters, so signing with HS512 for the wrong-algorithm case raises no key-length warning.
SECRET_KEY = "a-test-secret-key-long-enough-for-hs256-and-for-hs512-signatures"
OTHER_SECRET_KEY = "another-test-secret-key-long-enough-for-hs256-and-hs512-signing!"
TTL = timedelta(hours=1)
ISSUED_AT = datetime(2026, 10, 21, 10, 0, 0, tzinfo=UTC)


def tokens_at(clock: FixedClock) -> JwtAccessTokens:
    return JwtAccessTokens(SECRET_KEY, TTL, clock)


# PyJWT types its keys with `cryptography` classes, unknown without that optional package.
def claims(token: str) -> dict[str, object]:
    return jwt.decode(  # pyright: ignore[reportUnknownMemberType]
        token,
        SECRET_KEY,
        algorithms=["HS256"],
        options={"verify_exp": False, "verify_iat": False},
    )


def signed(payload: dict[str, object], key: str = SECRET_KEY, algorithm: str = "HS256") -> str:
    return jwt.encode(payload, key, algorithm=algorithm)  # pyright: ignore[reportUnknownMemberType]


def valid_claims() -> dict[str, object]:
    issued_at = int(ISSUED_AT.timestamp())
    return {
        "sub": UserIdMother.random().value,
        "iat": issued_at,
        "exp": issued_at + int(TTL.total_seconds()),
    }


def test_a_token_verifies_back_to_the_user_it_was_issued_for() -> None:
    tokens = tokens_at(FixedClock(ISSUED_AT))
    user_id = UserIdMother.random()

    token = tokens.issue(user_id)

    assert tokens.verify(token.value) == user_id


def test_a_token_carries_the_user_and_clock_based_issue_and_expiry_times() -> None:
    user_id = UserIdMother.random()

    token = tokens_at(FixedClock(ISSUED_AT)).issue(user_id)

    issued_at = int(ISSUED_AT.timestamp())
    assert claims(token.value) == {"sub": user_id.value, "iat": issued_at, "exp": issued_at + 3600}
    assert token.expires_in_seconds == 3600
    assert jwt.get_unverified_header(token.value)["alg"] == "HS256"


def test_a_token_is_valid_until_the_second_before_it_expires() -> None:
    clock = FixedClock(ISSUED_AT)
    tokens = tokens_at(clock)
    token = tokens.issue(UserIdMother.random())

    clock.advance(timedelta(minutes=59, seconds=59))
    tokens.verify(token.value)

    clock.advance(timedelta(seconds=1))
    with pytest.raises(InvalidAccessToken):
        tokens.verify(token.value)


def test_verification_ignores_the_system_clock() -> None:
    issued_long_ago = datetime(2001, 1, 1, tzinfo=UTC)
    tokens = tokens_at(FixedClock(issued_long_ago))

    tokens.verify(tokens.issue(UserIdMother.random()).value)


def _with_a_changed_character(token: str) -> str:
    signature_start = token.rindex(".") + 1
    changed = "A" if token[signature_start] != "A" else "B"
    return token[:signature_start] + changed + token[signature_start + 1 :]


def _unsigned(payload: dict[str, object]) -> str:
    def part(value: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=").decode()

    return f"{part({'alg': 'none', 'typ': 'JWT'})}.{part(payload)}."


def _without(claim: str) -> dict[str, object]:
    return {name: value for name, value in valid_claims().items() if name != claim}


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(signed(valid_claims(), key=OTHER_SECRET_KEY), id="another key"),
        pytest.param(_with_a_changed_character(signed(valid_claims())), id="changed character"),
        pytest.param(_unsigned(valid_claims()), id="alg none"),
        pytest.param(signed(valid_claims(), algorithm="HS512"), id="another algorithm"),
        pytest.param(signed(_without("sub")), id="no sub"),
        pytest.param(signed({**valid_claims(), "sub": "not-a-uuid"}), id="sub not a user id"),
        pytest.param(signed({**valid_claims(), "sub": 42}), id="sub not a string"),
        pytest.param(signed(_without("exp")), id="no exp"),
        pytest.param("not-a-token", id="garbage"),
        pytest.param("", id="empty"),
    ],
)
def test_rejects_a_token_it_cannot_trust(token: str) -> None:
    tokens = tokens_at(FixedClock(ISSUED_AT + timedelta(minutes=1)))

    with pytest.raises(InvalidAccessToken) as error:
        tokens.verify(token)

    assert str(error.value) == "Invalid or expired access token"
