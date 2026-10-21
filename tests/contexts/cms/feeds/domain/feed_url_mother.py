from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedUrl
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class FeedUrlMother:
    @staticmethod
    def create(value: str | None) -> FeedUrl:
        return FeedUrl(value)

    @staticmethod
    def random() -> FeedUrl:
        return FeedUrl(MotherCreator.url() if MotherCreator.boolean() else None)
