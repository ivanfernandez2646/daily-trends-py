from collections.abc import Sequence

import httpx
from dishka import AsyncContainer, Provider, make_async_container

from daily_trends_py.apps.cms_backend.providers.feeds import FEED_USE_CASES, FeedsProvider
from daily_trends_py.apps.cms_backend.providers.infrastructure import InfrastructureProvider
from daily_trends_py.apps.cms_backend.providers.users import USER_USE_CASES, UsersProvider
from daily_trends_py.apps.cms_backend.settings import Settings
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.migration import (  # noqa: E501
    Migration,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    MIGRATIONS,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
)

# Built when the app starts, not on the first request that needs them. Mongo is named on its own:
# its migrations and its connection check must not depend on a use case reaching it.
STARTUP_DEPENDENCIES: tuple[object, ...] = (MongoClient, *FEED_USE_CASES, *USER_USE_CASES)


def create_container(
    settings: Settings,
    *overrides: Provider,
    http_transport: httpx.AsyncBaseTransport | None = None,
    migrations: Sequence[Migration] = MIGRATIONS,
) -> AsyncContainer:
    """The app's composition root: the shared infrastructure plus one provider per subdomain.

    `overrides` are providers declared with `override=True`, such as fakes in tests.
    """
    return make_async_container(
        InfrastructureProvider(http_transport, migrations),
        FeedsProvider(),
        UsersProvider(),
        *overrides,
        context={Settings: settings},
    )
