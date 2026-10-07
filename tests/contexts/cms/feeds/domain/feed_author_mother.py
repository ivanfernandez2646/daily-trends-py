from daily_trends_py.contexts.cms.feeds.domain.feed_author import FeedAuthor
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class FeedAuthorMother:
    @staticmethod
    def create(value: str) -> FeedAuthor:
        return FeedAuthor(value)

    @staticmethod
    def random() -> FeedAuthor:
        return FeedAuthor(MotherCreator.name())
