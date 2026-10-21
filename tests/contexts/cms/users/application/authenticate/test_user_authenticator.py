import pytest

from daily_trends_py.contexts.cms.users.application.authenticate.user_authenticator import (
    UserAuthenticator,
)
from daily_trends_py.contexts.cms.users.domain.access_token import AccessToken
from daily_trends_py.contexts.cms.users.domain.errors import InvalidCredentials
from daily_trends_py.contexts.cms.users.domain.user import User
from tests.contexts.cms.users.domain.user_email_mother import UserEmailMother
from tests.contexts.cms.users.domain.user_mother import UserMother
from tests.contexts.cms.users.domain.user_password_hash_mother import UserPasswordHashMother
from tests.contexts.cms.users.fakes.fake_access_tokens import FakeAccessTokens
from tests.contexts.cms.users.fakes.fake_password_hasher import FakePasswordHasher
from tests.contexts.cms.users.fakes.in_memory_user_repository import InMemoryUserRepository

PASSWORD = "a-long-enough-secret"


def admin() -> User:
    return UserMother.random(
        email=UserEmailMother.create("admin@example.com"),
        password_hash=UserPasswordHashMother.create(f"hashed:{PASSWORD}"),
    )


def authenticator_with(
    users: list[User], hasher: FakePasswordHasher, tokens: FakeAccessTokens
) -> UserAuthenticator:
    return UserAuthenticator(InMemoryUserRepository(users), hasher, tokens)


@pytest.mark.parametrize("email", ["admin@example.com", "  Admin@Example.COM "])
async def test_valid_credentials_give_an_access_token_for_the_user(email: str) -> None:
    user, tokens = admin(), FakeAccessTokens(expires_in_seconds=600)

    token = await authenticator_with([user], FakePasswordHasher(), tokens).execute(
        email=email, password=PASSWORD
    )

    assert token == AccessToken(f"token-for:{user.id.value}", 600)
    assert tokens.issued_for == [user.id]


async def test_a_wrong_password_raises_invalid_credentials_without_a_token() -> None:
    user, hasher, tokens = admin(), FakePasswordHasher(), FakeAccessTokens()

    with pytest.raises(InvalidCredentials) as error:
        await authenticator_with([user], hasher, tokens).execute(
            email="admin@example.com", password="a-wrong-password"
        )

    assert str(error.value) == "Invalid email or password"
    assert hasher.verified == [("a-wrong-password", user.password_hash)]
    assert tokens.issued_for == []


@pytest.mark.parametrize("email", ["someone@example.com", "not-an-email", ""])
async def test_an_unknown_or_invalid_email_still_verifies_once_and_fails_the_same_way(
    email: str,
) -> None:
    hasher, tokens = FakePasswordHasher(), FakeAccessTokens()

    with pytest.raises(InvalidCredentials) as error:
        await authenticator_with([admin()], hasher, tokens).execute(email=email, password=PASSWORD)

    assert str(error.value) == "Invalid email or password"
    assert hasher.verified == [(PASSWORD, None)]
    assert tokens.issued_for == []
