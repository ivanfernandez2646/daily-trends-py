import pytest

from daily_trends_py.contexts.cms.feeds.application.update.feed_updater import FeedUpdater
from daily_trends_py.contexts.cms.feeds.domain.feed_not_found import FeedNotFound
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from tests.contexts.cms.feeds.domain.feed_description_mother import FeedDescriptionMother
from tests.contexts.cms.feeds.domain.feed_id_mother import FeedIdMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.deleted_after_find_feed_repository import (
    DeletedAfterFindFeedRepository,
)
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


async def test_raises_feed_not_found_without_writing_when_the_feed_does_not_exist() -> None:
    repository = InMemoryFeedRepository()
    updater = FeedUpdater(repository)
    id = FeedIdMother.random()

    with pytest.raises(FeedNotFound):
        await updater.execute({"id": id.value, "title": "A title"})

    assert repository.updated == []


async def test_raises_feed_not_found_when_the_feed_is_deleted_before_the_write() -> None:
    feed = FeedMother.random()
    repository = DeletedAfterFindFeedRepository([feed])

    with pytest.raises(FeedNotFound):
        await FeedUpdater(repository).execute({"id": feed.id.value, "title": "A new title"})

    assert repository.updated == []
    assert await repository.find(feed.id) is None


async def test_returns_the_stored_feed_without_writing_when_nothing_is_sent() -> None:
    feed = FeedMother.random()
    repository = InMemoryFeedRepository([feed])

    result = await FeedUpdater(repository).execute({"id": feed.id.value})

    assert result is feed
    assert repository.updated == []


async def test_returns_the_stored_feed_without_writing_when_the_values_are_the_same() -> None:
    feed = FeedMother.random()
    repository = InMemoryFeedRepository([feed])

    result = await FeedUpdater(repository).execute(
        {"id": feed.id.value, "title": feed.title.value, "description": feed.description.value}
    )

    assert result is feed
    assert repository.updated == []


async def test_updates_and_returns_the_updated_feed() -> None:
    feed = FeedMother.random()
    repository = InMemoryFeedRepository([feed])
    title, description = MotherCreator.sentence(), MotherCreator.sentence()

    result = await FeedUpdater(repository).execute(
        {"id": feed.id.value, "title": title, "description": description}
    )

    assert repository.updated == [result]
    assert result.updated_at.value is not None
    assert result.to_primitives() == {
        **feed.to_primitives(),
        "title": title,
        "description": description,
        "updatedAt": result.updated_at.value,
    }


async def test_an_absent_description_keeps_the_stored_one() -> None:
    feed = FeedMother.random(description=FeedDescriptionMother.create("A description"))
    repository = InMemoryFeedRepository([feed])

    result = await FeedUpdater(repository).execute({"id": feed.id.value, "title": "A new title"})

    assert result.title.value == "A new title"
    assert result.description.value == "A description"


@pytest.mark.parametrize("title", ["", "   "])
async def test_rejects_a_blank_title(title: str) -> None:
    feed = FeedMother.random()
    repository = InMemoryFeedRepository([feed])

    with pytest.raises(InvalidArgumentError) as error:
        await FeedUpdater(repository).execute({"id": feed.id.value, "title": title})

    assert str(error.value) == f"<FeedTitle> is mandatory. Current value: <{title}>"
    assert repository.updated == []


@pytest.mark.parametrize("description", [None, ""])
async def test_assigns_a_null_or_empty_description(description: str | None) -> None:
    feed = FeedMother.random(description=FeedDescriptionMother.create("A description"))
    repository = InMemoryFeedRepository([feed])

    result = await FeedUpdater(repository).execute(
        {"id": feed.id.value, "description": description}
    )

    assert result.description.value == description
    assert result.title == feed.title
    assert repository.updated == [result]


async def test_rejects_an_id_that_is_not_a_uuid() -> None:
    with pytest.raises(InvalidArgumentError) as error:
        await FeedUpdater(InMemoryFeedRepository()).execute({"id": "not-a-uuid"})

    assert str(error.value) == "<FeedId> does not allow the value <not-a-uuid>"


async def test_looks_for_the_feed_before_validating_the_title() -> None:
    with pytest.raises(FeedNotFound):
        await FeedUpdater(InMemoryFeedRepository()).execute(
            {"id": FeedIdMother.random().value, "title": "   "}
        )
