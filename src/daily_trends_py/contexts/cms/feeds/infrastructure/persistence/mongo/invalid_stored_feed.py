from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)


class InvalidStoredFeed(Exception):
    """A stored document the domain rejects: a server fault, never a client error."""

    def __init__(self, id: object, error: InvalidArgumentError) -> None:
        super().__init__(f"Stored feed <{id}> is invalid: {error}")
