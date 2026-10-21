from datetime import UTC, datetime

import pytest

from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.users.application.create.user_creator import UserCreator
from daily_trends_py.contexts.cms.users.domain.errors import UserAlreadyExists
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator
from tests.contexts.cms.shared.fakes.fixed_clock import FixedClock
from tests.contexts.cms.users.domain.user_email_mother import UserEmailMother
from tests.contexts.cms.users.domain.user_mother import UserMother
from tests.contexts.cms.users.fakes.fake_password_hasher import FakePasswordHasher
from tests.contexts.cms.users.fakes.in_memory_user_repository import InMemoryUserRepository

NOW = datetime(2026, 10, 21, 9, 30, tzinfo=UTC)


def creator_with(
    repository: InMemoryUserRepository | None = None, hasher: FakePasswordHasher | None = None
) -> UserCreator:
    return UserCreator(
        repository or InMemoryUserRepository(), hasher or FakePasswordHasher(), FixedClock(NOW)
    )


async def test_stores_a_user_with_the_normalized_email_and_the_hashed_password_created_now() -> (
    None
):
    repository = InMemoryUserRepository()
    password = MotherCreator.password()

    user = await creator_with(repository).execute(email=" Admin@Example.com ", password=password)

    assert repository.created == [user]
    assert user.email.value == "admin@example.com"
    assert user.password_hash.value == f"hashed:{password}"
    assert user.created_at.value == NOW


async def test_raises_user_already_exists_for_a_taken_email() -> None:
    stored = UserMother.random(email=UserEmailMother.create("admin@example.com"))
    repository = InMemoryUserRepository([stored])

    with pytest.raises(UserAlreadyExists) as error:
        await creator_with(repository).execute(
            email="ADMIN@example.com", password=MotherCreator.password()
        )

    assert str(error.value) == "User with email <admin@example.com> already exists"
    assert repository.created == []


@pytest.mark.parametrize(
    ("email", "password", "message"),
    [
        (
            "not-an-email",
            "a-long-enough-secret",
            "<UserEmail> does not allow the value <not-an-email>",
        ),
        ("admin@example.com", "shortsecret", "<UserPassword> must have at least 12 characters"),
    ],
)
async def test_rejects_an_invalid_email_or_a_short_password_before_hashing_or_saving(
    email: str, password: str, message: str
) -> None:
    repository, hasher = InMemoryUserRepository(), FakePasswordHasher()

    with pytest.raises(InvalidArgumentError) as error:
        await creator_with(repository, hasher).execute(email=email, password=password)

    assert str(error.value) == message
    assert hasher.hashed == []
    assert repository.created == []
