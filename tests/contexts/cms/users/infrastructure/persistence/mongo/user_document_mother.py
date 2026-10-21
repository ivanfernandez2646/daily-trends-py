from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDocument,
)
from daily_trends_py.contexts.cms.users.domain.user import User
from tests.contexts.cms.feeds.infrastructure.persistence.mongo.feed_document_mother import MISSING
from tests.contexts.cms.users.domain.user_mother import UserMother


class UserDocumentMother:
    """User documents as MongoDB stores them, to seed data this API would never write."""

    @staticmethod
    def create(user: User, **overrides: object) -> MongoDocument:
        """`user` as stored; an override replaces a stored field, `MISSING` removes it."""
        primitives = user.to_primitives()
        document: MongoDocument = {
            "_id": primitives["id"],
            "email": primitives["email"],
            "password_hash": primitives["password_hash"],
            "created_at": primitives["created_at"],
        }
        for field, value in overrides.items():
            if value is MISSING:
                del document[field]
            else:
                document[field] = value
        return document

    @staticmethod
    def random(**overrides: object) -> MongoDocument:
        return UserDocumentMother.create(UserMother.random(), **overrides)
