from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta, timezone

import pytest

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    m0003_users_indexes,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
    MongoCollection,
)
from daily_trends_py.contexts.cms.users.domain.errors import UserAlreadyExists
from daily_trends_py.contexts.cms.users.infrastructure.persistence.mongo.invalid_stored_user import (  # noqa: E501
    InvalidStoredUser,
)
from daily_trends_py.contexts.cms.users.infrastructure.persistence.mongo.mongo_user_repository import (  # noqa: E501
    MongoUserRepository,
)
from tests.contexts.cms.feeds.infrastructure.persistence.mongo.feed_document_mother import MISSING
from tests.contexts.cms.users.domain.user_created_at_mother import UserCreatedAtMother
from tests.contexts.cms.users.domain.user_email_mother import UserEmailMother
from tests.contexts.cms.users.domain.user_mother import UserMother
from tests.contexts.cms.users.infrastructure.persistence.mongo.user_document_mother import (
    UserDocumentMother,
)

pytestmark = pytest.mark.integration


@pytest.fixture
async def collection(mongo_client: MongoClient) -> AsyncIterator[MongoCollection]:
    collection = mongo_client.get_default_database()["users"]
    await collection.delete_many({})
    # The unique email index is what reports a duplicate.
    await m0003_users_indexes.up(mongo_client.get_default_database())
    yield collection
    await collection.delete_many({})


@pytest.fixture
def repository(mongo_client: MongoClient, collection: MongoCollection) -> MongoUserRepository:
    return MongoUserRepository(mongo_client)


async def test_creates_a_user_that_can_be_found_by_email(repository: MongoUserRepository) -> None:
    user = UserMother.random()

    await repository.create(user)

    found = await repository.find_by_email(user.email)
    assert found is not None
    assert found.to_primitives() == user.to_primitives()


async def test_find_by_email_returns_none_for_an_unknown_email(
    repository: MongoUserRepository,
) -> None:
    await repository.create(UserMother.random())

    assert await repository.find_by_email(UserEmailMother.random()) is None


async def test_stores_the_user_document_under_its_id_with_a_native_utc_date(
    repository: MongoUserRepository, collection: MongoCollection
) -> None:
    created_at = datetime(2026, 10, 21, 11, 30, 0, 123_000, tzinfo=timezone(timedelta(hours=2)))
    user = UserMother.random(created_at=UserCreatedAtMother.create(created_at))

    await repository.create(user)

    assert await collection.find_one({"_id": user.id.value}) == {
        "_id": user.id.value,
        "email": user.email.value,
        "password_hash": user.password_hash.value,
        "created_at": datetime(2026, 10, 21, 9, 30, 0, 123_000, tzinfo=UTC),
    }
    assert await collection.count_documents({"created_at": {"$type": "date"}}) == 1


async def test_create_on_an_existing_email_raises_and_keeps_only_the_original(
    repository: MongoUserRepository, collection: MongoCollection
) -> None:
    original = UserMother.random()
    await repository.create(original)

    with pytest.raises(UserAlreadyExists) as error:
        await repository.create(UserMother.random(email=original.email))

    assert str(error.value) == f"User with email <{original.email.value}> already exists"
    assert [doc["_id"] async for doc in collection.find()] == [original.id.value]


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        pytest.param(
            {"created_at": "2026-10-21T09:30:00.000Z"},
            "<UserCreatedAt> does not allow the value <2026-10-21T09:30:00.000Z>",
            id="ISO created at",
        ),
        pytest.param(
            {"created_at": MISSING},
            "<UserCreatedAt> does not allow the value <None>",
            id="missing created at",
        ),
        pytest.param(
            {"password_hash": ""},
            "<UserPasswordHash> is mandatory. Current value: <>",
            id="blank password hash",
        ),
        pytest.param(
            {"_id": "not-a-uuid"},
            "<UserId> does not allow the value <not-a-uuid>",
            id="invalid id",
        ),
    ],
)
async def test_find_by_email_raises_invalid_stored_user_for_a_broken_document(
    repository: MongoUserRepository,
    collection: MongoCollection,
    overrides: dict[str, object],
    reason: str,
) -> None:
    document = UserDocumentMother.random(**overrides)
    await collection.insert_one(document)

    with pytest.raises(InvalidStoredUser) as error:
        await repository.find_by_email(UserEmailMother.create(str(document["email"])))

    assert str(error.value) == f"Stored user <{document['_id']}> is invalid: {reason}"
