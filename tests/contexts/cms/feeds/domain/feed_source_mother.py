import random

from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource


class FeedSourceMother:
    @staticmethod
    def random() -> FeedSource:
        return random.choice(list(FeedSource))
