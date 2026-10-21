from collections.abc import AsyncIterator

import httpx
import pytest
from dishka import AsyncContainer
from pymongo.errors import InvalidOperation

from daily_trends_py.apps.cms_backend.container import create_container
from daily_trends_py.apps.cms_backend.providers.feeds import FEED_USE_CASES
from daily_trends_py.apps.cms_backend.settings import Settings
from daily_trends_py.contexts.cms.feeds.domain.feed_repository import FeedRepository
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
)
from tests.apps.cms_backend.fakes_provider import FakesProvider
from tests.apps.cms_backend.isolated_settings import IsolatedSettings
from tests.contexts.cms.feeds.fakes.in_memory_feed_repository import InMemoryFeedRepository
from tests.mongo import TEST_MONGO_URL


@pytest.fixture
def settings() -> Settings:
    return IsolatedSettings(mongo_url=TEST_MONGO_URL)


@pytest.fixture
async def container(settings: Settings) -> AsyncIterator[AsyncContainer]:
    container = create_container(settings)
    yield container
    await container.close()


@pytest.mark.integration
async def test_resolves_every_feed_use_case(container: AsyncContainer) -> None:
    for use_case in FEED_USE_CASES:
        assert isinstance(await container.get(use_case), use_case)


@pytest.mark.integration
async def test_resolves_one_instance_per_container(container: AsyncContainer) -> None:
    assert await container.get(FeedRepository) is await container.get(FeedRepository)


@pytest.mark.integration
async def test_closing_the_container_closes_its_resources(settings: Settings) -> None:
    container = create_container(settings)
    mongo_client = await container.get(MongoClient)
    http_client = await container.get(httpx.AsyncClient)

    await container.close()

    assert http_client.is_closed
    with pytest.raises(InvalidOperation):
        await mongo_client.admin.command("ping")


async def test_an_override_provider_replaces_a_dependency(settings: Settings) -> None:
    container = create_container(settings, FakesProvider())

    repository = await container.get(FeedRepository)

    assert isinstance(repository, InMemoryFeedRepository)
    await container.close()


async def test_the_http_client_uses_the_given_transport(settings: Settings) -> None:
    transport = httpx.MockTransport(lambda _request: httpx.Response(204))
    container = create_container(settings, http_transport=transport)
    http_client = await container.get(httpx.AsyncClient)

    response = await http_client.get("https://example.com")

    assert response.status_code == 204
    assert response.request.headers["user-agent"] == "daily-trends-py"
    await container.close()
