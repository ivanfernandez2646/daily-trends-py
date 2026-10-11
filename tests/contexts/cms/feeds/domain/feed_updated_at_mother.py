from datetime import datetime

from daily_trends_py.contexts.cms.feeds.domain.feed_updated_at import FeedUpdatedAt
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class FeedUpdatedAtMother:
    @staticmethod
    def create(value: datetime | str | None) -> FeedUpdatedAt:
        """An ISO-8601 string keeps fixed dates readable in tests."""
        return FeedUpdatedAt(datetime.fromisoformat(value) if isinstance(value, str) else value)

    @staticmethod
    def random() -> FeedUpdatedAt:
        return FeedUpdatedAt(MotherCreator.date_time() if MotherCreator.boolean() else None)
