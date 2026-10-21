from daily_trends_py.contexts.cms.shared.domain.clock import Clock
from daily_trends_py.contexts.cms.users.domain.password_hasher import PasswordHasher
from daily_trends_py.contexts.cms.users.domain.user import User
from daily_trends_py.contexts.cms.users.domain.user_repository import UserRepository
from daily_trends_py.contexts.cms.users.domain.value_objects import (
    UserEmail,
    UserId,
    UserPassword,
)


class UserCreator:
    def __init__(self, repository: UserRepository, hasher: PasswordHasher, clock: Clock) -> None:
        self._repository = repository
        self._hasher = hasher
        self._clock = clock

    async def execute(self, *, email: str, password: str) -> User:
        user_email = UserEmail(email)
        password_hash = await self._hasher.hash(UserPassword(password))
        user = User.create(
            id=UserId.random(),
            email=user_email,
            password_hash=password_hash,
            now=self._clock.now(),
        )
        await self._repository.create(user)
        return user
