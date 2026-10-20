from daily_trends_py.contexts.cms.feeds.domain.errors import FeedAlreadyExists, FeedNotFound
from daily_trends_py.contexts.cms.shared.domain.conflict_error import ConflictError
from daily_trends_py.contexts.cms.shared.domain.not_found_error import NotFoundError
from tests.contexts.cms.feeds.domain.feed_id_mother import FeedIdMother


def test_feed_not_found_is_a_not_found_error() -> None:
    id = FeedIdMother.random()

    error = FeedNotFound(id)

    assert isinstance(error, NotFoundError)
    assert str(error) == f"Feed with id <{id.value}> not found"


def test_feed_already_exists_is_a_conflict_error() -> None:
    id = FeedIdMother.random()

    error = FeedAlreadyExists(id)

    assert isinstance(error, ConflictError)
    assert str(error) == f"Feed with id <{id.value}> already exists"
