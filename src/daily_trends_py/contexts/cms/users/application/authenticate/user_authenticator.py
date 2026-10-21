from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.users.domain.access_token import AccessToken
from daily_trends_py.contexts.cms.users.domain.access_token_issuer import AccessTokenIssuer
from daily_trends_py.contexts.cms.users.domain.errors import InvalidCredentials
from daily_trends_py.contexts.cms.users.domain.password_hasher import PasswordHasher
from daily_trends_py.contexts.cms.users.domain.user import User
from daily_trends_py.contexts.cms.users.domain.user_repository import UserRepository
from daily_trends_py.contexts.cms.users.domain.value_objects import UserEmail


class UserAuthenticator:
    def __init__(
        self, repository: UserRepository, hasher: PasswordHasher, issuer: AccessTokenIssuer
    ) -> None:
        self._repository = repository
        self._hasher = hasher
        self._issuer = issuer

    async def execute(self, *, email: str, password: str) -> AccessToken:
        user = await self._find(email)
        # An unknown email still verifies a password, so it answers as slowly as a wrong one.
        verified = await self._hasher.verify(password, None if user is None else user.password_hash)
        if user is None or not verified:
            raise InvalidCredentials()
        return self._issuer.issue(user.id)

    async def _find(self, email: str) -> User | None:
        try:
            user_email = UserEmail(email)
        except InvalidArgumentError:
            # No user can have it, so it is an unknown email rather than a bad request.
            return None
        return await self._repository.find_by_email(user_email)
