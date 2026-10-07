from daily_trends_py.contexts.cms.feeds.domain.feed_description import FeedDescription
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class FeedDescriptionMother:
    @staticmethod
    def create(value: str | None) -> FeedDescription:
        return FeedDescription(value)

    @staticmethod
    def random() -> FeedDescription:
        return FeedDescription(MotherCreator.sentence() if MotherCreator.boolean() else None)
