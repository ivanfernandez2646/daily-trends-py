from daily_trends_py.contexts.cms.feeds.domain.feed import Feed, FeedPrimitives
from daily_trends_py.contexts.cms.feeds.domain.feed_author import FeedAuthor
from daily_trends_py.contexts.cms.feeds.domain.feed_created_at import FeedCreatedAt
from daily_trends_py.contexts.cms.feeds.domain.feed_description import FeedDescription
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle
from daily_trends_py.contexts.cms.feeds.domain.feed_updated_at import FeedUpdatedAt
from tests.contexts.cms.feeds.domain.feed_author_mother import FeedAuthorMother
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_description_mother import FeedDescriptionMother
from tests.contexts.cms.feeds.domain.feed_id_mother import FeedIdMother
from tests.contexts.cms.feeds.domain.feed_source_mother import FeedSourceMother
from tests.contexts.cms.feeds.domain.feed_title_mother import FeedTitleMother
from tests.contexts.cms.feeds.domain.feed_updated_at_mother import FeedUpdatedAtMother


class FeedMother:
    @staticmethod
    def random(
        *,
        id: FeedId | None = None,
        title: FeedTitle | None = None,
        description: FeedDescription | None = None,
        author: FeedAuthor | None = None,
        source: FeedSource | None = None,
        created_at: FeedCreatedAt | None = None,
        updated_at: FeedUpdatedAt | None = None,
    ) -> Feed:
        return Feed(
            id=id or FeedIdMother.random(),
            title=title or FeedTitleMother.random(),
            description=description or FeedDescriptionMother.random(),
            author=author or FeedAuthorMother.random(),
            source=source or FeedSourceMother.random(),
            created_at=created_at or FeedCreatedAtMother.random(),
            updated_at=updated_at or FeedUpdatedAtMother.random(),
        )

    @staticmethod
    def from_primitives(primitives: FeedPrimitives) -> Feed:
        return Feed.from_primitives(primitives)
