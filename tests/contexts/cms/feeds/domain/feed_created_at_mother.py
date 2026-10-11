from datetime import datetime

from daily_trends_py.contexts.cms.feeds.domain.feed_created_at import FeedCreatedAt
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class FeedCreatedAtMother:
    @staticmethod
    def create(value: datetime | str) -> FeedCreatedAt:
        """An ISO-8601 string keeps fixed dates readable in tests."""
        return FeedCreatedAt(datetime.fromisoformat(value) if isinstance(value, str) else value)

    @staticmethod
    def random() -> FeedCreatedAt:
        return FeedCreatedAt(MotherCreator.date_time())

    @staticmethod
    def now() -> FeedCreatedAt:
        return FeedCreatedAt.now()
