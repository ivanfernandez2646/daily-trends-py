from datetime import datetime
from typing import NotRequired, Self, TypedDict

from pydantic import BaseModel, ConfigDict, with_config

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedSource

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


class FeedResponse(BaseModel):
    id: str
    title: str
    description: str | None
    author: str
    source: FeedSource
    created_at: datetime
    updated_at: datetime | None

    @classmethod
    def from_feed(cls, feed: Feed) -> Self:
        return cls(
            id=feed.id.value,
            title=feed.title.value,
            description=feed.description.value,
            author=feed.author.value,
            source=feed.source,
            created_at=feed.created_at.value,
            updated_at=feed.updated_at.value,
        )


class ErrorResponse(BaseModel):
    error: str
