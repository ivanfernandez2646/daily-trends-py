from datetime import timedelta

# dishka types `provide` with an unparametrized `classmethod`; the providers below are typed.
from dishka import (
    AnyOf,
    Provider,
    Scope,
    provide,  # pyright: ignore[reportUnknownVariableType]
)

from daily_trends_py.apps.cms_backend.settings import Settings
from daily_trends_py.contexts.cms.shared.domain.clock import Clock
from daily_trends_py.contexts.cms.users.application.authenticate.user_authenticator import (
    UserAuthenticator,
)
from daily_trends_py.contexts.cms.users.application.create.user_creator import UserCreator
from daily_trends_py.contexts.cms.users.application.find_session.admin_session_finder import (
    AdminSessionFinder,
)
from daily_trends_py.contexts.cms.users.domain.access_token_issuer import AccessTokenIssuer
from daily_trends_py.contexts.cms.users.domain.access_token_verifier import AccessTokenVerifier
from daily_trends_py.contexts.cms.users.domain.password_hasher import PasswordHasher
from daily_trends_py.contexts.cms.users.domain.user_repository import UserRepository
from daily_trends_py.contexts.cms.users.infrastructure.hashing.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from daily_trends_py.contexts.cms.users.infrastructure.persistence.mongo.mongo_user_repository import (  # noqa: E501
    MongoUserRepository,
)
from daily_trends_py.contexts.cms.users.infrastructure.tokens.jwt_access_tokens import (
    JwtAccessTokens,
)

USER_USE_CASES = (UserCreator, UserAuthenticator, AdminSessionFinder)


class UsersProvider(Provider):
    """The users subdomain: its repository, password hashing, access tokens and use cases."""

    scope = Scope.APP

    user_repository = provide(MongoUserRepository, provides=UserRepository)
    password_hasher = provide(Argon2PasswordHasher, provides=PasswordHasher)

    user_creator = provide(UserCreator)
    user_authenticator = provide(UserAuthenticator)
    admin_session_finder = provide(AdminSessionFinder)

    @provide
    def access_tokens(
        self, settings: Settings, clock: Clock
    ) -> AnyOf[JwtAccessTokens, AccessTokenIssuer, AccessTokenVerifier]:
        return JwtAccessTokens(
            settings.auth_secret_key.get_secret_value(),
            timedelta(seconds=settings.auth_token_ttl_seconds),
            clock,
        )
