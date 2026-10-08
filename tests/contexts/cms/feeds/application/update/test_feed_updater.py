import pytest

from daily_trends_py.contexts.cms.feeds.application.update.feed_updater import (
    FeedUpdater,
    FeedUpdaterProps,
)
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_not_found import FeedNotFound
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.raw_value import MISSING
from tests.contexts.cms.feeds.domain.feed_description_mother import FeedDescriptionMother
from tests.contexts.cms.feeds.domain.feed_id_mother import FeedIdMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


def props_for(feed: Feed, **overrides: object) -> FeedUpdaterProps:
    props: FeedUpdaterProps = {"id": feed.id.value, "title": MISSING, "description": MISSING}
    return props | overrides  # pyright: ignore[reportReturnType]


async def test_raises_feed_not_found_without_saving_when_the_feed_does_not_exist() -> None:
    repository = InMemoryFeedRepository()
    updater = FeedUpdater(repository)
    id = FeedIdMother.random()

    with pytest.raises(FeedNotFound):
        await updater.execute({"id": id.value, "title": "A title", "description": MISSING})

    assert repository.saved == []


async def test_returns_the_stored_feed_without_saving_when_nothing_is_sent() -> None:
    feed = FeedMother.random()
    repository = InMemoryFeedRepository([feed])

    result = await FeedUpdater(repository).execute(props_for(feed))

    assert result is feed
    assert repository.saved == []


async def test_returns_the_stored_feed_without_saving_when_the_values_are_the_same() -> None:
    feed = FeedMother.random()
    repository = InMemoryFeedRepository([feed])

    result = await FeedUpdater(repository).execute(
        props_for(feed, title=feed.title.value, description=feed.description.value)
    )

    assert result is feed
    assert repository.saved == []


async def test_saves_and_returns_the_updated_feed() -> None:
    feed = FeedMother.random()
    repository = InMemoryFeedRepository([feed])
    title, description = MotherCreator.sentence(), MotherCreator.sentence()

    result = await FeedUpdater(repository).execute(
        props_for(feed, title=title, description=description)
    )

    assert repository.saved == [result]
    assert result.updated_at.value is not None
    assert result.to_primitives() == {
        **feed.to_primitives(),
        "title": title,
        "description": description,
        "updatedAt": result.updated_at.value,
    }


@pytest.mark.parametrize(
    ("title", "rendered"),
    [
        ("", ""),
        ("   ", "   "),
        (None, "null"),
        (False, "false"),
        (0, "0"),
        (0.0, "0"),
        ([], ""),
        ({}, "[object Object]"),
        (5, "5"),
    ],
)
async def test_rejects_a_present_title_that_is_blank_or_not_a_string(
    title: object, rendered: str
) -> None:
    feed = FeedMother.random()
    repository = InMemoryFeedRepository([feed])

    with pytest.raises(InvalidArgumentError) as error:
        await FeedUpdater(repository).execute(props_for(feed, title=title))

    assert str(error.value) == f"<FeedTitle> is mandatory. Current value: <{rendered}>"
    assert repository.saved == []


async def test_rejects_a_description_that_is_not_a_string() -> None:
    feed = FeedMother.random()

    with pytest.raises(InvalidArgumentError) as error:
        await FeedUpdater(InMemoryFeedRepository([feed])).execute(props_for(feed, description=5))

    assert str(error.value) == "<FeedDescription> does not allow the value <5>"


@pytest.mark.parametrize("description", [None, ""])
async def test_assigns_a_null_or_empty_description(description: str | None) -> None:
    feed = FeedMother.random(description=FeedDescriptionMother.create("A description"))
    repository = InMemoryFeedRepository([feed])

    result = await FeedUpdater(repository).execute(props_for(feed, description=description))

    assert result.description.value == description
    assert repository.saved == [result]


async def test_rejects_an_id_that_is_not_a_uuid() -> None:
    with pytest.raises(InvalidArgumentError):
        await FeedUpdater(InMemoryFeedRepository()).execute(
            {"id": "not-a-uuid", "title": MISSING, "description": MISSING}
        )


async def test_looks_for_the_feed_before_validating_the_title() -> None:
    with pytest.raises(FeedNotFound):
        await FeedUpdater(InMemoryFeedRepository()).execute(
            {"id": FeedIdMother.random().value, "title": "   ", "description": 5}
        )
