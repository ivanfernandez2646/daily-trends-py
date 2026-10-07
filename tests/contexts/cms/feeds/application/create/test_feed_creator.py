from datetime import UTC, datetime, timedelta

import pytest

from daily_trends_py.contexts.cms.feeds.application.create.feed_creator import (
    FeedCreator,
    FeedCreatorProps,
)
from daily_trends_py.contexts.cms.feeds.domain.feed_already_exists import FeedAlreadyExists
from daily_trends_py.contexts.cms.feeds.domain.feed_created_domain_event import (
    FeedCreatedDomainEvent,
)
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.raw_value import MISSING
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator
from tests.contexts.cms.shared.fakes.recording_event_bus import RecordingEventBus


def random_props(**overrides: object) -> FeedCreatorProps:
    props: FeedCreatorProps = {
        "id": MotherCreator.uuid(),
        "title": MotherCreator.sentence(),
        "description": MotherCreator.sentence() if MotherCreator.boolean() else None,
        "author": MotherCreator.name(),
        "source": FeedSource.CMS,
    }
    return props | overrides  # pyright: ignore[reportReturnType]


async def test_saves_and_returns_a_new_feed_without_update_date() -> None:
    repository = InMemoryFeedRepository()
    creator = FeedCreator(repository, RecordingEventBus())
    props = random_props()
    before = datetime.now(UTC)

    feed = await creator.execute(props)

    assert repository.saved == [feed]
    primitives = feed.to_primitives()
    assert {key: primitives[key] for key in props} == props
    assert primitives["updatedAt"] is None
    assert before - timedelta(milliseconds=1) <= datetime.fromisoformat(primitives["createdAt"])


async def test_publishes_feed_created() -> None:
    event_bus = RecordingEventBus()
    creator = FeedCreator(InMemoryFeedRepository(), event_bus)
    props = random_props()

    await creator.execute(props)

    [event] = event_bus.published
    assert isinstance(event, FeedCreatedDomainEvent)
    assert (event.aggregate_id, event.title) == (props["id"], props["title"])


async def test_raises_feed_already_exists_without_saving_or_publishing() -> None:
    existing = FeedMother.random()
    repository = InMemoryFeedRepository([existing])
    event_bus = RecordingEventBus()
    creator = FeedCreator(repository, event_bus)

    with pytest.raises(FeedAlreadyExists) as error:
        await creator.execute(random_props(id=existing.id.value))

    assert str(error.value) == f"Feed with id <{existing.id.value}> already exists"
    assert repository.saved == []
    assert event_bus.published == []


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"id": "bad", "title": " ", "author": ""}, "<FeedId> does not allow the value <bad>"),
        ({"title": " ", "author": ""}, "<FeedTitle> is mandatory. Current value: < >"),
        ({"author": ""}, "<FeedAuthor> is mandatory. Current value: <>"),
    ],
)
async def test_raises_the_first_invalid_argument_in_field_order(
    overrides: dict[str, str], message: str
) -> None:
    repository = InMemoryFeedRepository()
    creator = FeedCreator(repository, RecordingEventBus())

    with pytest.raises(InvalidArgumentError) as error:
        await creator.execute(random_props(**overrides))

    assert str(error.value) == message
    assert repository.searched_ids == []


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"title": MISSING}, "<FeedTitle> is mandatory. Current value: <undefined>"),
        ({"title": None}, "<FeedTitle> is mandatory. Current value: <null>"),
        ({"author": 123}, "<FeedAuthor> is mandatory. Current value: <123>"),
        ({"description": True}, "<FeedDescription> does not allow the value <true>"),
    ],
)
async def test_rejects_missing_null_or_non_string_raw_values(
    overrides: dict[str, object], message: str
) -> None:
    creator = FeedCreator(InMemoryFeedRepository(), RecordingEventBus())

    with pytest.raises(InvalidArgumentError) as error:
        await creator.execute(random_props(**overrides))

    assert str(error.value) == message


async def test_a_missing_description_is_stored_as_null() -> None:
    creator = FeedCreator(InMemoryFeedRepository(), RecordingEventBus())

    feed = await creator.execute(random_props(description=MISSING))

    assert feed.description.value is None
