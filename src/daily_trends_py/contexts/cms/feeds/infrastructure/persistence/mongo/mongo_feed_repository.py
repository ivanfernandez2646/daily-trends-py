from typing import cast

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed, FeedPrimitives
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_repository import (
    MongoRepository,
)


class MongoFeedRepository(MongoRepository):
    def __init__(self, client: MongoClient) -> None:
        super().__init__(client, "feeds")

    async def save(self, feed: Feed) -> None:
        await self._persist(feed.id.value, feed.to_primitives())

    async def find(self, id: FeedId) -> Feed | None:
        document = await self._by_id(id.value)
        if document is None:
            return None
        # Documents are only written by `save`; the value objects validate them on the way back.
        return Feed.from_primitives(cast(FeedPrimitives, document))
