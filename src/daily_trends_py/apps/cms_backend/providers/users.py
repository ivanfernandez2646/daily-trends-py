# dishka types `provide` with an unparametrized `classmethod`; the providers below are typed.
from dishka import (
    Provider,
    Scope,
    provide,  # pyright: ignore[reportUnknownVariableType]
)

from daily_trends_py.contexts.cms.users.application.create.user_creator import UserCreator
from daily_trends_py.contexts.cms.users.domain.password_hasher import PasswordHasher
from daily_trends_py.contexts.cms.users.domain.user_repository import UserRepository
from daily_trends_py.contexts.cms.users.infrastructure.hashing.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from daily_trends_py.contexts.cms.users.infrastructure.persistence.mongo.mongo_user_repository import (  # noqa: E501
    MongoUserRepository,
)

USER_USE_CASES = (UserCreator,)


class UsersProvider(Provider):
    """The users subdomain: its repository, password hashing and use cases."""

    scope = Scope.APP

    user_repository = provide(MongoUserRepository, provides=UserRepository)
    password_hasher = provide(Argon2PasswordHasher, provides=PasswordHasher)

    user_creator = provide(UserCreator)
