import pytest
from dishka import AsyncContainer
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource
from tests.apps.cms_backend.conftest import resolve, run_in_app
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother
from tests.contexts.cms.feeds.domain.feed_updated_at_mother import FeedUpdatedAtMother

pytestmark = pytest.mark.integration

scenarios("features/list-feed.feature")

UNKNOWN_CATEGORY = (
    "query.category: Input should be 'POLITICS', 'INTERNATIONAL', 'ECONOMY', 'SOCIETY', 'SPORTS',"
    " 'CULTURE', 'TECHNOLOGY', 'SCIENCE', 'HEALTH', 'OPINION' or 'OTHER'"
)
UNKNOWN_SOURCE = (
    "query.source: Input should be 'CMS', 'EL_PAIS', 'EL_MUNDO', 'EL_ESPANOL', 'EL_CONFIDENCIAL',"
    " 'LA_RAZON' or 'LA_VANGUARDIA'"
)


def _store(container: AsyncContainer, client: TestClient, *feeds: Feed) -> None:
    repository = resolve(client, container, FeedRepository)
    for feed in feeds:
        run_in_app(client, lambda feed=feed: repository.create(feed))


def test_lists_feeds_chronologically_with_utc_dates_and_a_fraction_only_when_not_zero(
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
    _store(container, client, earlier, later)

    response = client.get("/feed/list")

    assert response.status_code == 200
    assert [(feed["id"], feed["created_at"], feed["updated_at"]) for feed in response.json()] == [
        (later.id.value, "2026-10-09T09:30:00Z", "2026-10-10T07:15:30.250000Z"),
        (earlier.id.value, "2026-10-09T08:00:00Z", None),
    ]


def test_lists_only_the_feeds_of_the_given_category_newest_first(
    container: AsyncContainer, client: TestClient
) -> None:
    older = FeedMother.random(
        category=FeedCategory.SPORTS,
        created_at=FeedCreatedAtMother.create("2026-10-18T10:00:00.000Z"),
    )
    newer = FeedMother.random(
        category=FeedCategory.SPORTS,
        created_at=FeedCreatedAtMother.create("2026-10-20T10:00:00.000Z"),
    )
    culture = FeedMother.random(category=FeedCategory.CULTURE)
    _store(container, client, older, culture, newer)

    response = client.get("/feed/list", params={"category": "SPORTS"})

    assert response.status_code == 200
    assert [feed["id"] for feed in response.json()] == [newer.id.value, older.id.value]


def test_lists_nothing_when_no_feed_has_the_category(
    container: AsyncContainer, client: TestClient
) -> None:
    _store(container, client, FeedMother.random(category=FeedCategory.CULTURE))

    response = client.get("/feed/list", params={"category": "HEALTH"})

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("category", ["nope", "sports", ""])
def test_a_category_that_is_not_a_known_value_answers_400(
    client: TestClient, category: str
) -> None:
    response = client.get("/feed/list", params={"category": category})

    assert response.status_code == 400
    assert response.json() == {"error": UNKNOWN_CATEGORY}


def test_lists_only_the_feeds_of_the_given_source(
    container: AsyncContainer, client: TestClient
) -> None:
    cms = FeedMother.random(source=FeedSource.CMS)
    el_mundo = FeedMother.random(source=FeedSource.EL_MUNDO)
    _store(container, client, cms, el_mundo)

    response = client.get("/feed/list", params={"source": "CMS"})

    assert response.status_code == 200
    assert [feed["id"] for feed in response.json()] == [cms.id.value]


def test_lists_only_the_feeds_that_match_both_the_category_and_the_source(
    container: AsyncContainer, client: TestClient
) -> None:
    el_mundo_sports = FeedMother.random(source=FeedSource.EL_MUNDO, category=FeedCategory.SPORTS)
    el_mundo_culture = FeedMother.random(source=FeedSource.EL_MUNDO, category=FeedCategory.CULTURE)
    cms_sports = FeedMother.random(source=FeedSource.CMS, category=FeedCategory.SPORTS)
    _store(container, client, el_mundo_sports, el_mundo_culture, cms_sports)

    response = client.get("/feed/list", params={"category": "SPORTS", "source": "EL_MUNDO"})

    assert response.status_code == 200
    assert [feed["id"] for feed in response.json()] == [el_mundo_sports.id.value]


@pytest.mark.parametrize("source", ["nope", "el_mundo", ""])
def test_a_source_that_is_not_a_known_value_answers_400(client: TestClient, source: str) -> None:
    response = client.get("/feed/list", params={"source": source})

    assert response.status_code == 400
    assert response.json() == {"error": UNKNOWN_SOURCE}
