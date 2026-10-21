from daily_trends_py.contexts.cms.shared.domain.conflict_error import ConflictError
from daily_trends_py.contexts.cms.shared.domain.unauthorized_error import UnauthorizedError
from daily_trends_py.contexts.cms.users.domain.value_objects import UserEmail


class UserAlreadyExists(ConflictError):
    def __init__(self, email: UserEmail) -> None:
        super().__init__(f"User with email <{email.value}> already exists")


class InvalidCredentials(UnauthorizedError):
    """The same for an unknown email and a wrong password, so neither reveals which emails exist."""

    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class InvalidAccessToken(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__("Invalid or expired access token")


class MissingAccessToken(UnauthorizedError):
    def __init__(self) -> None:
        super().__init__("Authentication required")
