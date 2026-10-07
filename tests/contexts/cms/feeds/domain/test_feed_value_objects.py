import pytest

from daily_trends_py.contexts.cms.feeds.domain.feed_author import FeedAuthor
from daily_trends_py.contexts.cms.feeds.domain.feed_description import FeedDescription
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from tests.contexts.cms.feeds.domain.feed_id_mother import FeedIdMother
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


def test_feed_id_rejects_a_value_that_is_not_a_uuid() -> None:
    with pytest.raises(InvalidArgumentError) as error:
        FeedId("not-a-uuid")

    assert str(error.value) == "<FeedId> does not allow the value <not-a-uuid>"


def test_feed_id_keeps_a_valid_uuid() -> None:
    value = MotherCreator.uuid()

    assert FeedIdMother.create(value).value == value


@pytest.mark.parametrize("required_string", [FeedTitle, FeedAuthor])
def test_title_and_author_are_mandatory(required_string: type[FeedTitle | FeedAuthor]) -> None:
    with pytest.raises(InvalidArgumentError) as error:
        required_string("")

    assert str(error.value) == f"<{required_string.__name__}> is mandatory. Current value: <>"


@pytest.mark.parametrize("value", [None, ""])
def test_feed_description_is_optional(value: str | None) -> None:
    assert FeedDescription(value).value == value
