from daily_trends_py.contexts.cms.users.infrastructure.hashing.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from tests.contexts.cms.users.domain.user_password_mother import UserPasswordMother


async def test_verifies_its_own_hash_of_a_password() -> None:
    hasher = Argon2PasswordHasher()
    password = UserPasswordMother.random()

    hash = await hasher.hash(password)

    assert hash.value != password.value
    assert hash.value.startswith("$argon2id$")
    assert await hasher.verify(password.value, hash)


async def test_rejects_a_wrong_password() -> None:
    hasher = Argon2PasswordHasher()
    hash = await hasher.hash(UserPasswordMother.random())

    assert not await hasher.verify(UserPasswordMother.random().value, hash)


async def test_salts_every_hash() -> None:
    hasher = Argon2PasswordHasher()
    password = UserPasswordMother.random()

    assert await hasher.hash(password) != await hasher.hash(password)


async def test_rejects_any_password_without_a_hash() -> None:
    hasher = Argon2PasswordHasher()

    assert not await hasher.verify(UserPasswordMother.random().value, None)
    assert not await hasher.verify("", None)
