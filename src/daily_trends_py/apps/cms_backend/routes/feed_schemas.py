from typing import NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, with_config

# Strict: a number, boolean, list or object is never coerced into a string. Unknown fields are
# ignored, Pydantic's default.
_STRICT = ConfigDict(strict=True)


class CreateFeedRequest(BaseModel):
    model_config = _STRICT

    title: str
    author: str
    description: str | None = None


@with_config(_STRICT)
class UpdateFeedRequest(TypedDict):
    """Only the fields that were sent: an absent key keeps the value, `null` is a value."""

    title: NotRequired[str]
    description: NotRequired[str | None]
