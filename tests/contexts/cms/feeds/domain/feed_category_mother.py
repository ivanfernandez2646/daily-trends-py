import random

from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory


class FeedCategoryMother:
    @staticmethod
    def random() -> FeedCategory:
        return random.choice(list(FeedCategory))

    @staticmethod
    def other_than(category: FeedCategory) -> FeedCategory:
        return random.choice([other for other in FeedCategory if other != category])
