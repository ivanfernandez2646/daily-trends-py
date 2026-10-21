from dataclasses import dataclass, field


@dataclass(frozen=True)
class AccessToken:
    """A signed token that proves who the caller is until it expires."""

    value: str = field(repr=False)
    expires_in_seconds: int
