from typing import Protocol

from daily_trends_py.contexts.cms.users.domain.value_objects import UserPassword, UserPasswordHash


class PasswordHasher(Protocol):
    async def hash(self, password: UserPassword) -> UserPasswordHash: ...

    async def verify(self, password: str, hash: UserPasswordHash | None) -> bool:
        """Whether `password` matches `hash`.

        Without a hash it checks a dummy one and answers `False`, so a login for an unknown email
        takes as long as a wrong password.
        """
        ...
