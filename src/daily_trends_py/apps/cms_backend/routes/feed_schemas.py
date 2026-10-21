from datetime import datetime
from typing import Annotated, NotRequired, Self, TypedDict

from pydantic import BaseModel, ConfigDict, Field, Strict, with_config

from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory, FeedSource

# Strict: a number, boolean, list or object is never coerced into a string. Unknown fields are
# ignored, Pydantic's default.
_STRICT = ConfigDict(strict=True)
# Strict mode only takes enum instances, and the decoded body holds the category as a string.
# Lax enum validation still accepts nothing but one of the values.
_Category = Annotated[FeedCategory, Strict(False)]


class CreateFeedRequest(BaseModel):
    model_config = _STRICT

    title: str
    author: str
    category: _Category
    description: str | None = None


@with_config(_STRICT)
class UpdateFeedRequest(TypedDict):
    """Only the fields that were sent: an absent key keeps the value, `null` is a value."""

    title: NotRequired[str]
    description: NotRequired[str | None]
    category: NotRequired[_Category]


class FeedResponse(BaseModel):
    id: str
    title: str
    description: str | None
    author: str
    source: FeedSource
    category: FeedCategory
    url: str | None
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
            category=feed.category,
            url=feed.url.value,
            created_at=feed.created_at.value,
            updated_at=feed.updated_at.value,
        )


class FeedPageResponse(BaseModel):
    items: list[FeedResponse]
    next_cursor: str | None = Field(
        description="Pass it as `cursor` to get the next page; `null` on the last page."
    )


class ErrorResponse(BaseModel):
    error: str
