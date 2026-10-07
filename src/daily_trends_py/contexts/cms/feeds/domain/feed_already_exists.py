from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId


class FeedAlreadyExists(Exception):
    def __init__(self, id: FeedId) -> None:
        super().__init__(f"Feed with id <{id.value}> already exists")
