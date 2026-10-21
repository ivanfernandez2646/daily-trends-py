from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict

from daily_trends_py.contexts.cms.feeds.domain.events import FeedCreatedDomainEvent
from daily_trends_py.contexts.cms.feeds.domain.value_objects import (
    FeedAuthor,
    FeedCategory,
    FeedCreatedAt,
    FeedDescription,
    FeedId,
    FeedSource,
    FeedTitle,
    FeedUpdatedAt,
    FeedUrl,
)
from daily_trends_py.contexts.cms.shared.domain.aggregate_root import AggregateRoot


class FeedPrimitives(TypedDict):
    id: str
    title: str
    description: str | None
    author: str
    source: FeedSource
    category: FeedCategory
    url: str | None
    created_at: datetime
    updated_at: datetime | None


@dataclass(eq=False)
class Feed(AggregateRoot):
    id: FeedId
    title: FeedTitle
    description: FeedDescription
    author: FeedAuthor
    source: FeedSource
    category: FeedCategory
    url: FeedUrl
    created_at: FeedCreatedAt
    updated_at: FeedUpdatedAt

    @classmethod
    def create(
        cls,
        *,
        id: FeedId,
        title: FeedTitle,
        description: FeedDescription,
        author: FeedAuthor,
        source: FeedSource,
        category: FeedCategory,
        url: FeedUrl,
        now: datetime,
    ) -> Feed:
        feed = cls(
            id=id,
            title=title,
            description=description,
            author=author,
            source=source,
            category=category,
            url=url,
            created_at=FeedCreatedAt(now),
            updated_at=FeedUpdatedAt(None),
        )
        feed.record(
            FeedCreatedDomainEvent(
                aggregate_id=id.value, title=title.value, occurred_on=feed.created_at.value
            )
        )
        return feed

    @classmethod
    def from_primitives(cls, primitives: FeedPrimitives) -> Feed:
        return cls(
            id=FeedId(primitives["id"]),
            title=FeedTitle(primitives["title"]),
            description=FeedDescription(primitives["description"]),
            author=FeedAuthor(primitives["author"]),
            source=FeedSource(primitives["source"]),
            category=FeedCategory(primitives["category"]),
            url=FeedUrl(primitives["url"]),
            created_at=FeedCreatedAt(primitives["created_at"]),
            updated_at=FeedUpdatedAt(primitives["updated_at"]),
        )

    def update(
        self,
        *,
        now: datetime,
        title: FeedTitle | None = None,
        description: FeedDescription | None = None,
        category: FeedCategory | None = None,
    ) -> Feed | None:
        """Return the updated feed, or `None` if nothing changes; `None` keeps a value."""
        new_title = self.title if title is None else title
        new_description = self.description if description is None else description
        new_category = self.category if category is None else category
        if (new_title, new_description, new_category) == (
            self.title,
            self.description,
            self.category,
        ):
            return None
        updated = Feed(
            id=self.id,
            title=new_title,
            description=new_description,
            author=self.author,
            source=self.source,
            category=new_category,
            url=self.url,
            created_at=self.created_at,
            updated_at=FeedUpdatedAt(now),
        )
        updated._keep_events_of(self)
        return updated

    def to_primitives(self) -> FeedPrimitives:
        return {
            "id": self.id.value,
            "title": self.title.value,
            "description": self.description.value,
            "author": self.author.value,
            "source": self.source,
            "category": self.category,
            "url": self.url.value,
            "created_at": self.created_at.value,
            "updated_at": self.updated_at.value,
        }
