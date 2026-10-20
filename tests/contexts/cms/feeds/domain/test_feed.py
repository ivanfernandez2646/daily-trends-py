from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed, FeedPrimitives
from daily_trends_py.contexts.cms.feeds.domain.feed_created_domain_event import (
    FeedCreatedDomainEvent,
)
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from tests.contexts.cms.feeds.domain.feed_author_mother import FeedAuthorMother
from tests.contexts.cms.feeds.domain.feed_description_mother import FeedDescriptionMother
from tests.contexts.cms.feeds.domain.feed_id_mother import FeedIdMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.domain.feed_title_mother import FeedTitleMother
from tests.contexts.cms.feeds.domain.feed_updated_at_mother import FeedUpdatedAtMother
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator

NOW = datetime(2026, 10, 20, 9, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("description", "updated_at"),
    [(None, None), ("A description", datetime(2026, 10, 7, 12, 0, tzinfo=UTC))],
)
def test_primitives_round_trip_keeps_every_field_in_order(
    description: str | None, updated_at: datetime | None
) -> None:
    primitives: FeedPrimitives = {
        "id": MotherCreator.uuid(),
        "title": "A title",
        "description": description,
        "author": "An author",
        "source": FeedSource.CMS,
        "created_at": MotherCreator.date_time(),
        "updated_at": updated_at,
    }

    result = Feed.from_primitives(primitives).to_primitives()

    assert result == primitives
    assert list(result) == list(primitives)


def test_create_sets_creation_dates_and_records_feed_created_at_now() -> None:
    id, title = FeedIdMother.random(), FeedTitleMother.random()

    feed = Feed.create(
        id=id,
        title=title,
        description=FeedDescriptionMother.random(),
        author=FeedAuthorMother.random(),
        source=FeedSource.CMS,
        now=NOW,
    )

    assert feed.created_at.value == NOW
    assert feed.created_at.value.tzinfo is UTC
    assert feed.updated_at.value is None
    [event] = feed.pull_domain_events()
    assert isinstance(event, FeedCreatedDomainEvent)
    assert event.event_name == "feed.created"
    assert (event.aggregate_id, event.title, event.occurred_on) == (id.value, title.value, NOW)


def test_update_returns_none_and_records_nothing_when_nothing_changes() -> None:
    feed = FeedMother.random()

    assert feed.update(now=NOW) is None
    assert feed.update(now=NOW, title=feed.title, description=feed.description) is None
    assert feed.pull_domain_events() == []


def test_update_returns_a_new_feed_with_the_new_title_updated_now() -> None:
    feed = FeedMother.random(updated_at=FeedUpdatedAtMother.create(None))
    title = FeedTitleMother.random()

    updated = feed.update(now=NOW, title=title)

    assert updated is not None
    assert updated.to_primitives() == {
        **feed.to_primitives(),
        "title": title.value,
        "updated_at": NOW,
    }
    assert updated.pull_domain_events() == []


def test_update_keeps_the_pending_events_of_the_original_feed() -> None:
    id = FeedIdMother.random()
    feed = Feed.create(
        id=id,
        title=FeedTitleMother.random(),
        description=FeedDescriptionMother.random(),
        author=FeedAuthorMother.random(),
        source=FeedSource.CMS,
        now=NOW,
    )

    updated = feed.update(now=NOW, title=FeedTitleMother.random())

    assert updated is not None
    [event] = updated.pull_domain_events()
    assert isinstance(event, FeedCreatedDomainEvent)
    assert event.aggregate_id == id.value


def test_create_and_update_store_a_business_time_instant_in_utc() -> None:
    madrid_now = datetime(2026, 10, 20, 11, 30, tzinfo=ZoneInfo("Europe/Madrid"))
    feed = Feed.create(
        id=FeedIdMother.random(),
        title=FeedTitleMother.random(),
        description=FeedDescriptionMother.random(),
        author=FeedAuthorMother.random(),
        source=FeedSource.CMS,
        now=madrid_now,
    )

    updated = feed.update(now=madrid_now, title=FeedTitleMother.random())

    assert updated is not None
    assert feed.created_at.value == datetime(2026, 10, 20, 9, 30, tzinfo=UTC)
    assert feed.created_at.value.tzinfo is UTC
    assert updated.updated_at.value is not None
    assert updated.updated_at.value == feed.created_at.value
    assert updated.updated_at.value.tzinfo is UTC


def test_update_sets_the_description_to_null() -> None:
    feed = FeedMother.random(description=FeedDescriptionMother.create("A description"))

    updated = feed.update(now=NOW, description=FeedDescriptionMother.create(None))

    assert updated is not None
    assert updated.description.value is None
