import pytest
from dishka import AsyncContainer
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from tests.apps.cms_backend.conftest import resolve, run_in_app
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.domain.feed_updated_at_mother import FeedUpdatedAtMother

pytestmark = pytest.mark.integration

scenarios("features/list-feed.feature")


def test_lists_feeds_chronologically_with_utc_dates_in_milliseconds(
    container: AsyncContainer, client: TestClient
) -> None:
    earlier = FeedMother.random(
        created_at=FeedCreatedAtMother.create("2026-10-09T10:00:00.000+02:00"),
        updated_at=FeedUpdatedAtMother.create(None),
    )
    later = FeedMother.random(
        created_at=FeedCreatedAtMother.create("2026-10-09T09:30:00.000Z"),
        updated_at=FeedUpdatedAtMother.create("2026-10-10T07:15:30.250+00:00"),
    )
    repository = resolve(client, container, FeedRepository)
    for feed in (earlier, later):
        run_in_app(client, lambda feed=feed: repository.save(feed))

    response = client.get("/feed/list")

    assert response.status_code == 200
    assert [(feed["id"], feed["createdAt"], feed["updatedAt"]) for feed in response.json()] == [
        (later.id.value, "2026-10-09T09:30:00.000Z", "2026-10-10T07:15:30.250Z"),
        (earlier.id.value, "2026-10-09T08:00:00.000Z", None),
    ]
