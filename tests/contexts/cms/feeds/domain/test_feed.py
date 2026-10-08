from datetime import UTC, datetime, timedelta

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


@pytest.mark.parametrize(
    ("description", "updated_at"),
    [(None, None), ("A description", "2026-10-07T12:00:00.000Z")],
)
def test_primitives_round_trip_keeps_every_field_in_order(
    description: str | None, updated_at: str | None
) -> None:
    primitives: FeedPrimitives = {
        "id": MotherCreator.uuid(),
        "title": "A title",
        "description": description,
        "author": "An author",
        "source": FeedSource.CMS,
        "createdAt": MotherCreator.iso_date_time(),
        "updatedAt": updated_at,
    }

    result = Feed.from_primitives(primitives).to_primitives()

    assert result == primitives
    assert list(result) == list(primitives)


def test_create_sets_creation_dates_and_records_feed_created() -> None:
    before = datetime.now(UTC)
    id, title = FeedIdMother.random(), FeedTitleMother.random()

    feed = Feed.create(
        id=id,
        title=title,
        description=FeedDescriptionMother.random(),
        author=FeedAuthorMother.random(),
        source=FeedSource.CMS,
    )

    assert feed.updated_at.value is None
    assert before - timedelta(milliseconds=1) <= datetime.fromisoformat(feed.created_at.value)
    [event] = feed.pull_domain_events()
    assert isinstance(event, FeedCreatedDomainEvent)
    assert event.event_name == "feed.created"
    assert (event.aggregate_id, event.title) == (id.value, title.value)


def test_update_returns_none_when_nothing_changes() -> None:
    feed = FeedMother.random()

    assert feed.update() is None
    assert feed.update(title=feed.title, description=feed.description) is None


def test_update_returns_a_new_feed_with_the_new_title_and_update_date() -> None:
    feed = FeedMother.random(updated_at=FeedUpdatedAtMother.create(None))
    title = FeedTitleMother.random()
    before = datetime.now(UTC)

    updated = feed.update(title=title)

    assert updated is not None
    assert updated.to_primitives() == {
        **feed.to_primitives(),
        "title": title.value,
        "updatedAt": updated.updated_at.value,
    }
    assert updated.updated_at.value is not None
    assert before - timedelta(milliseconds=1) <= datetime.fromisoformat(updated.updated_at.value)
    assert updated.pull_domain_events() == []


def test_update_sets_the_description_to_null() -> None:
    feed = FeedMother.random(description=FeedDescriptionMother.create("A description"))

    updated = feed.update(description=FeedDescriptionMother.create(None))

    assert updated is not None
    assert updated.description.value is None
