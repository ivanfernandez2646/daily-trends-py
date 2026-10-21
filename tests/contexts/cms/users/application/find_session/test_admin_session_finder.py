from datetime import UTC, datetime

import pytest

from daily_trends_py.contexts.cms.users.application.find_session.admin_session_finder import (
    AdminSession,
    AdminSessionFinder,
)
from daily_trends_py.contexts.cms.users.domain.errors import InvalidAccessToken
from daily_trends_py.contexts.cms.users.domain.verified_access_token import VerifiedAccessToken
from tests.contexts.cms.users.domain.user_id_mother import UserIdMother
from tests.contexts.cms.users.domain.user_mother import UserMother
from tests.contexts.cms.users.fakes.in_memory_user_repository import InMemoryUserRepository

EXPIRES_AT = datetime(2026, 10, 21, 18, 0, 0, tzinfo=UTC)


async def test_answers_the_token_user_and_its_expiry() -> None:
    user = UserMother.random()
    finder = AdminSessionFinder(InMemoryUserRepository([user]))

    session = await finder.execute(VerifiedAccessToken(user.id, EXPIRES_AT))

    assert session == AdminSession(user=user, token_expires_at=EXPIRES_AT)


async def test_a_token_whose_user_no_longer_exists_raises_invalid_access_token() -> None:
    finder = AdminSessionFinder(InMemoryUserRepository([UserMother.random()]))

    with pytest.raises(InvalidAccessToken):
        await finder.execute(VerifiedAccessToken(UserIdMother.random(), EXPIRES_AT))
