import pytest

from daily_trends_py.contexts.cms.users.domain.errors import UserAlreadyExists
from tests.contexts.cms.users.domain.user_email_mother import UserEmailMother
from tests.contexts.cms.users.domain.user_id_mother import UserIdMother
from tests.contexts.cms.users.domain.user_mother import UserMother
from tests.contexts.cms.users.fakes.in_memory_user_repository import InMemoryUserRepository


async def test_finds_a_created_user_by_email() -> None:
    repository = InMemoryUserRepository()
    user = UserMother.random()

    await repository.create(user)

    assert await repository.find_by_email(user.email) is user
    assert await repository.find_by_email(UserEmailMother.random()) is None


async def test_finds_a_created_user_by_id() -> None:
    repository = InMemoryUserRepository()
    user = UserMother.random()

    await repository.create(user)

    assert await repository.find_by_id(user.id) is user
    assert await repository.find_by_id(UserIdMother.random()) is None


async def test_create_on_an_existing_email_raises_and_keeps_the_stored_user() -> None:
    stored = UserMother.random()
    repository = InMemoryUserRepository([stored])

    with pytest.raises(UserAlreadyExists):
        await repository.create(UserMother.random(email=stored.email))

    assert await repository.find_by_email(stored.email) is stored
    assert repository.created == []
