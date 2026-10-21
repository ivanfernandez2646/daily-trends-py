from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict

from daily_trends_py.contexts.cms.shared.domain.aggregate_root import AggregateRoot
from daily_trends_py.contexts.cms.users.domain.value_objects import (
    UserCreatedAt,
    UserEmail,
    UserId,
    UserPasswordHash,
)


class UserPrimitives(TypedDict):
    id: str
    email: str
    password_hash: str
    created_at: datetime


@dataclass(eq=False)
class User(AggregateRoot):
    """An administrator: every user manages the CMS, so there are no roles."""

    id: UserId
    email: UserEmail
    password_hash: UserPasswordHash
    created_at: UserCreatedAt

    @classmethod
    def create(
        cls, *, id: UserId, email: UserEmail, password_hash: UserPasswordHash, now: datetime
    ) -> User:
        return cls(id=id, email=email, password_hash=password_hash, created_at=UserCreatedAt(now))

    @classmethod
    def from_primitives(cls, primitives: UserPrimitives) -> User:
        return cls(
            id=UserId(primitives["id"]),
            email=UserEmail(primitives["email"]),
            password_hash=UserPasswordHash(primitives["password_hash"]),
            created_at=UserCreatedAt(primitives["created_at"]),
        )

    def to_primitives(self) -> UserPrimitives:
        return {
            "id": self.id.value,
            "email": self.email.value,
            "password_hash": self.password_hash.value,
            "created_at": self.created_at.value,
        }
