from collections.abc import Mapping
from typing import Any

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
from daily_trends_py.contexts.cms.users.domain.errors import UserAlreadyExists
from daily_trends_py.contexts.cms.users.domain.user import User
from daily_trends_py.contexts.cms.users.domain.value_objects import UserEmail, UserId
from daily_trends_py.contexts.cms.users.infrastructure.persistence.mongo.invalid_stored_user import (  # noqa: E501
    InvalidStoredUser,
)


class MongoUserRepository(MongoRepository):
    def __init__(self, client: MongoClient) -> None:
        super().__init__(client, "users")

    async def create(self, user: User) -> None:
        primitives = user.to_primitives()
        document: MongoDocument = {
            "_id": primitives["id"],
            "email": primitives["email"],
            "password_hash": primitives["password_hash"],
            "created_at": primitives["created_at"],
        }
        if not await self._insert(document, unique_key="email"):
            raise UserAlreadyExists(user.email)

    async def find_by_email(self, email: UserEmail) -> User | None:
        document = await self._find_one({"email": email.value})
        if document is None:
            return None
        return _to_user(document)

    async def find_by_id(self, id: UserId) -> User | None:
        document = await self._find_one({"_id": id.value})
        if document is None:
            return None
        return _to_user(document)


def _to_user(document: MongoDocument) -> User:
    # BSON values are only known at runtime: the value objects check them, and a missing field
    # reads as `None`, which they reject.
    stored: Mapping[str, Any] = document

    def field(name: str) -> Any:
        return stored.get(name)

    try:
        return User.from_primitives(
            {
                "id": field("_id"),
                "email": field("email"),
                "password_hash": field("password_hash"),
                "created_at": field("created_at"),
            }
        )
    except InvalidArgumentError as error:
        raise InvalidStoredUser(stored.get("_id"), error) from error
