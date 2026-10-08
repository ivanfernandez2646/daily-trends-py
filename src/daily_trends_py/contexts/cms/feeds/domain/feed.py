from dataclasses import dataclass, replace
from typing import TypedDict

from daily_trends_py.contexts.cms.feeds.domain.feed_author import FeedAuthor
from daily_trends_py.contexts.cms.feeds.domain.feed_created_domain_event import (
    FeedCreatedDomainEvent,
)
from daily_trends_py.contexts.cms.feeds.domain.feed_description import FeedDescription
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle
from daily_trends_py.contexts.cms.shared.domain.aggregate_root import AggregateRoot
from daily_trends_py.contexts.cms.shared.domain.date_time_value_object import (
    DateTimeValueObject,
    RequiredDateTimeValueObject,
)


class FeedPrimitives(TypedDict):
    id: str
    title: str
    description: str | None
    author: str
    source: FeedSource
    createdAt: str
    updatedAt: str | None


@dataclass(eq=False)
class Feed(AggregateRoot):
    id: FeedId
    title: FeedTitle
    description: FeedDescription
    author: FeedAuthor
    source: FeedSource
    created_at: RequiredDateTimeValueObject
    updated_at: DateTimeValueObject

    @classmethod
    def create(
        cls,
        *,
        id: FeedId,
        title: FeedTitle,
        description: FeedDescription,
        author: FeedAuthor,
        source: FeedSource,
    ) -> Feed:
        feed = cls(
            id=id,
            title=title,
            description=description,
            author=author,
            source=source,
            created_at=RequiredDateTimeValueObject.now(),
            updated_at=DateTimeValueObject(None),
        )
        feed.record(FeedCreatedDomainEvent(aggregate_id=id.value, title=title.value))
        return feed

    @classmethod
    def from_primitives(cls, primitives: FeedPrimitives) -> Feed:
        return cls(
            id=FeedId(primitives["id"]),
            title=FeedTitle(primitives["title"]),
            description=FeedDescription(primitives["description"]),
            author=FeedAuthor(primitives["author"]),
            source=FeedSource(primitives["source"]),
            created_at=RequiredDateTimeValueObject(primitives["createdAt"]),
            updated_at=DateTimeValueObject(primitives["updatedAt"]),
        )

    def update(
        self, *, title: FeedTitle | None = None, description: FeedDescription | None = None
    ) -> Feed | None:
        """Return the updated feed, or `None` if nothing changes; `None` keeps a value."""
        new_title = self.title if title is None else title
        new_description = self.description if description is None else description
        if new_title == self.title and new_description == self.description:
            return None
        return replace(
            self,
            title=new_title,
            description=new_description,
            updated_at=DateTimeValueObject.now(),
        )

    def to_primitives(self) -> FeedPrimitives:
        return {
            "id": self.id.value,
            "title": self.title.value,
            "description": self.description.value,
            "author": self.author.value,
            "source": self.source,
            "createdAt": self.created_at.value,
            "updatedAt": self.updated_at.value,
        }
