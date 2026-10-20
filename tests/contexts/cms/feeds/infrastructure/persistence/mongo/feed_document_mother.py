from typing import Final

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDocument,
)
from tests.contexts.cms.feeds.domain.feed_mother import FeedMother

MISSING: Final = object()


class FeedDocumentMother:
    """Feed documents as MongoDB stores them, to seed data this API would never write."""

    @staticmethod
    def create(feed: Feed, **overrides: object) -> MongoDocument:
        """`feed` as stored; an override replaces a stored field, `MISSING` removes it."""
        primitives = feed.to_primitives()
        document: MongoDocument = {
            "_id": primitives["id"],
            "title": primitives["title"],
            "description": primitives["description"],
            "author": primitives["author"],
            "source": primitives["source"].value,
            "createdAt": primitives["created_at"],
            "updatedAt": primitives["updated_at"],
        }
        for field, value in overrides.items():
            if value is MISSING:
                del document[field]
            else:
                document[field] = value
        return document

    @staticmethod
    def random(**overrides: object) -> MongoDocument:
        return FeedDocumentMother.create(FeedMother.random(), **overrides)
