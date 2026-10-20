from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedId
from daily_trends_py.contexts.cms.shared.domain.conflict_error import ConflictError
from daily_trends_py.contexts.cms.shared.domain.not_found_error import NotFoundError


class FeedAlreadyExists(ConflictError):
    def __init__(self, id: FeedId) -> None:
        super().__init__(f"Feed with id <{id.value}> already exists")


class FeedNotFound(NotFoundError):
    def __init__(self, id: FeedId) -> None:
        super().__init__(f"Feed with id <{id.value}> not found")
