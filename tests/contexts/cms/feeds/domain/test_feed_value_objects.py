import pytest

from daily_trends_py.contexts.cms.feeds.domain.feed_author import FeedAuthor
from daily_trends_py.contexts.cms.feeds.domain.feed_created_at import FeedCreatedAt
from daily_trends_py.contexts.cms.feeds.domain.feed_description import FeedDescription
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_title import FeedTitle
from daily_trends_py.contexts.cms.feeds.domain.feed_updated_at import FeedUpdatedAt
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


@pytest.mark.parametrize("date_time", [FeedCreatedAt, FeedUpdatedAt])
def test_feed_dates_name_themselves_when_the_value_is_not_a_date(
    date_time: type[FeedCreatedAt | FeedUpdatedAt],
) -> None:
    with pytest.raises(InvalidArgumentError) as error:
        date_time("not-a-date")

    assert str(error.value) == f"<{date_time.__name__}> does not allow the value <not-a-date>"


def test_feed_created_at_is_mandatory_and_feed_updated_at_is_optional() -> None:
    with pytest.raises(InvalidArgumentError):
        FeedCreatedAt("")

    assert FeedUpdatedAt(None).value is None
