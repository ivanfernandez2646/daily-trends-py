from collections.abc import Mapping
from datetime import datetime
from typing import Any

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
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

# Domain names that MongoDB stores under another name, for documents and criteria alike.
_STORED_NAMES = {"id": "_id", "created_at": "createdAt", "updated_at": "updatedAt"}


class MongoFeedRepository(MongoRepository):
    def __init__(self, client: MongoClient) -> None:
        super().__init__(client, "feeds")

    async def create(self, feed: Feed) -> None:
        if not await self._insert(_to_document(feed)):
            raise FeedAlreadyExists(feed.id)

    async def update(self, feed: Feed) -> None:
        if not await self._update(_to_document(feed)):
            raise FeedNotFound(feed.id)

    async def find(self, id: FeedId) -> Feed | None:
        document = await self._by_id(id.value)
        if document is None:
            return None
        return _to_feed(document)

    async def delete(self, feed: Feed) -> None:
        await self._remove(feed.id.value)

    async def search(self, criteria: FeedCriteria) -> list[Feed]:
        documents = await self._by_criteria(criteria, _STORED_NAMES)
        return [_to_feed(document) for document in documents]

    async def exists_headline(
        self, source: FeedSource, title: FeedTitle, since: datetime, until: datetime
    ) -> bool:
        return await self._exists(
            {
                "source": source,
                "title": title.value,
                _stored("created_at"): {"$gte": since, "$lt": until},
            }
        )


def _stored(name: str) -> str:
    return _STORED_NAMES.get(name, name)


def _to_document(feed: Feed) -> MongoDocument:
    return {_stored(name): value for name, value in feed.to_primitives().items()}


def _to_feed(document: MongoDocument) -> Feed:
    # BSON values are only known at runtime: the value objects check them, and a missing field
    # reads as `None`, which they reject when the field is required.
    stored: Mapping[str, Any] = document

    def field(name: str) -> Any:
        return stored.get(_stored(name))

    try:
        return Feed.from_primitives(
            {
                "id": field("id"),
                "title": field("title"),
                "description": field("description"),
                "author": field("author"),
                "source": field("source"),
                "created_at": field("created_at"),
                "updated_at": field("updated_at"),
            }
        )
    except InvalidArgumentError as error:
        raise InvalidStoredFeed(field("id"), error) from error
