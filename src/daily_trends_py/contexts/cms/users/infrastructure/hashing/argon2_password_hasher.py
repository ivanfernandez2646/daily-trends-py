import asyncio
import secrets

from pwdlib import PasswordHash

from daily_trends_py.contexts.cms.users.domain.value_objects import UserPassword, UserPasswordHash


class Argon2PasswordHasher:
    """Argon2id with the parameters `pwdlib` recommends.

    Hashing is deliberately slow, so it runs in a thread and never blocks the event loop.
    """

    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()
        self._dummy_hash: str | None = None

    async def hash(self, password: UserPassword) -> UserPasswordHash:
        return UserPasswordHash(await asyncio.to_thread(self._password_hash.hash, password.value))

    async def verify(self, password: str, hash: UserPasswordHash | None) -> bool:
        if hash is None:
            await asyncio.to_thread(self._password_hash.verify, password, await self._dummy())
            return False
        return await asyncio.to_thread(self._password_hash.verify, password, hash.value)

    async def _dummy(self) -> str:
        # Built on first use, so starting the app costs no hash.
        if self._dummy_hash is None:
            self._dummy_hash = await asyncio.to_thread(
                self._password_hash.hash, secrets.token_urlsafe(32)
            )
        return self._dummy_hash
