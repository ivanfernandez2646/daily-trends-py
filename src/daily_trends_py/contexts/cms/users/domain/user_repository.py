from typing import Protocol

from daily_trends_py.contexts.cms.users.domain.user import User
from daily_trends_py.contexts.cms.users.domain.value_objects import UserEmail, UserId


class UserRepository(Protocol):
    async def create(self, user: User) -> None:
        """Insert a new user; raises `UserAlreadyExists` and stores nothing if its email is used."""
        ...

    async def find_by_email(self, email: UserEmail) -> User | None: ...

    async def find_by_id(self, id: UserId) -> User | None: ...
