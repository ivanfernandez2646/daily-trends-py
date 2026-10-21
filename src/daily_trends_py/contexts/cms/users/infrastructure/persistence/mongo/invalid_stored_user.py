from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)


class InvalidStoredUser(Exception):
    """A stored document the domain rejects: a server fault, never a client error."""

    def __init__(self, id: object, error: InvalidArgumentError) -> None:
        super().__init__(f"Stored user <{id}> is invalid: {error}")
