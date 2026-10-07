from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class FeedIdMother:
    @staticmethod
    def create(value: str) -> FeedId:
        return FeedId(value)

    @staticmethod
    def random() -> FeedId:
        return FeedId(MotherCreator.uuid())
