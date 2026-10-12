from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, Self

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)


class MigrationModule(Protocol):
    __name__: str

    async def up(self, db: MongoDatabase) -> None: ...


@dataclass(frozen=True)
class Migration:
    id: str
    up: Callable[[MongoDatabase], Awaitable[None]]

    @classmethod
    def from_module(cls, module: MigrationModule) -> Self:
        return cls(module.__name__.rpartition(".")[2], module.up)
