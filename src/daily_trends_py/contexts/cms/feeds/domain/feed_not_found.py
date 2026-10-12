from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.shared.domain.not_found_error import NotFoundError


class FeedNotFound(NotFoundError):
    def __init__(self, id: FeedId) -> None:
        super().__init__(f"Feed with id <{id.value}> not found")
