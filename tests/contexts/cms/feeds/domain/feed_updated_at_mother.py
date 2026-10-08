from daily_trends_py.contexts.cms.feeds.domain.feed_updated_at import FeedUpdatedAt
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class FeedUpdatedAtMother:
    @staticmethod
    def create(value: str | None) -> FeedUpdatedAt:
        return FeedUpdatedAt(value)

    @staticmethod
    def random() -> FeedUpdatedAt:
        return FeedUpdatedAt(MotherCreator.iso_date_time() if MotherCreator.boolean() else None)
