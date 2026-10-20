import random

from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedSource


class FeedSourceMother:
    @staticmethod
    def random() -> FeedSource:
        return random.choice(list(FeedSource))
