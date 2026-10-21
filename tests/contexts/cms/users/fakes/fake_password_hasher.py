from daily_trends_py.contexts.cms.users.domain.value_objects import UserPassword, UserPasswordHash

PREFIX = "hashed:"


class FakePasswordHasher:
    """Hashes `x` as `hashed:x` and records what it hashed and verified."""

    def __init__(self) -> None:
        self.hashed: list[str] = []
        self.verified: list[tuple[str, UserPasswordHash | None]] = []

    async def hash(self, password: UserPassword) -> UserPasswordHash:
        self.hashed.append(password.value)
        return UserPasswordHash(f"{PREFIX}{password.value}")

    async def verify(self, password: str, hash: UserPasswordHash | None) -> bool:
        self.verified.append((password, hash))
        return hash is not None and hash.value == f"{PREFIX}{password}"
