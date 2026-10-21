from daily_trends_py.contexts.cms.users.domain.errors import UserAlreadyExists
from daily_trends_py.contexts.cms.users.domain.user import User
from daily_trends_py.contexts.cms.users.domain.value_objects import UserEmail


class InMemoryUserRepository:
    def __init__(self, users: list[User] | None = None) -> None:
        self._users = {user.email.value: user for user in users or []}
        self.created: list[User] = []

    async def create(self, user: User) -> None:
        if user.email.value in self._users:
            raise UserAlreadyExists(user.email)
        self._users[user.email.value] = user
        self.created.append(user)

    async def find_by_email(self, email: UserEmail) -> User | None:
        return self._users.get(email.value)
