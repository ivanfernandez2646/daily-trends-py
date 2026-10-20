from datetime import datetime
from typing import cast

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed, FeedPrimitives
from daily_trends_py.contexts.cms.feeds.domain.feed_already_exists import FeedAlreadyExists
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_not_found import FeedNotFound
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle
from daily_trends_py.contexts.cms.feeds.infrastructure.persistence.mongo.invalid_stored_feed import (  # noqa: E501
    InvalidStoredFeed,
)
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoClient,
    MongoDocument,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_repository import (
    MongoRepository,
)

_STORAGE_FIELDS = {"id": "_id", "created_at": "createdAt", "updated_at": "updatedAt"}


class MongoFeedRepository(MongoRepository):
    def __init__(self, client: MongoClient) -> None:
        super().__init__(client, "feeds")

    async def create(self, feed: Feed) -> None:
        if not await self._insert(feed.id.value, feed.to_primitives()):
            raise FeedAlreadyExists(feed.id)

    async def update(self, feed: Feed) -> None:
        if not await self._update(feed.id.value, feed.to_primitives()):
            raise FeedNotFound(feed.id)

    async def find(self, id: FeedId) -> Feed | None:
        document = await self._by_id(id.value)
        if document is None:
            return None
        return _to_feed(document)

    async def delete(self, feed: Feed) -> None:
        await self._remove(feed.id.value)

    async def search(self, criteria: FeedCriteria) -> list[Feed]:
        documents = await self._by_criteria(criteria, _STORAGE_FIELDS)
        return [_to_feed(document) for document in documents]

    async def exists_headline(
        self, source: FeedSource, title: FeedTitle, since: datetime, until: datetime
    ) -> bool:
        return await self._exists(
            {
                "source": source,
                "title": title.value,
                "createdAt": {"$gte": since, "$lt": until},
            }
        )


def _to_feed(document: MongoDocument) -> Feed:
    try:
        # A missing `createdAt` is rejected like any other value that is not a date.
        return Feed.from_primitives(cast(FeedPrimitives, {"createdAt": None, **document}))
    except InvalidArgumentError as error:
        raise InvalidStoredFeed(document["id"], error) from error
