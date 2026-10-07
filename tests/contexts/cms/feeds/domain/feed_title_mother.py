from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class FeedTitleMother:
    @staticmethod
    def create(value: str) -> FeedTitle:
        return FeedTitle(value)

    @staticmethod
    def random() -> FeedTitle:
        return FeedTitle(MotherCreator.sentence())
