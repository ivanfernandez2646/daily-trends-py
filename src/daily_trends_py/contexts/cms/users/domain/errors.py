from daily_trends_py.contexts.cms.shared.domain.conflict_error import ConflictError
from daily_trends_py.contexts.cms.users.domain.value_objects import UserEmail


class UserAlreadyExists(ConflictError):
    def __init__(self, email: UserEmail) -> None:
        super().__init__(f"User with email <{email.value}> already exists")
