from daily_trends_py.contexts.cms.feeds.domain.feed_created_at import FeedCreatedAt
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class FeedCreatedAtMother:
    @staticmethod
    def create(value: str) -> FeedCreatedAt:
        return FeedCreatedAt(value)

    @staticmethod
    def random() -> FeedCreatedAt:
        return FeedCreatedAt(MotherCreator.iso_date_time())

    @staticmethod
    def now() -> FeedCreatedAt:
        return FeedCreatedAt.now()
