import pytest

from daily_trends_py.contexts.cms.feeds.domain.value_objects import (
    FeedAuthor,
    FeedCategory,
    FeedCreatedAt,
    FeedDescription,
    FeedId,
    FeedSource,
    FeedTitle,
    FeedUpdatedAt,
    FeedUrl,
)
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
        date_time("not-a-date")  # pyright: ignore[reportArgumentType]

    assert str(error.value) == f"<{date_time.__name__}> does not allow the value <not-a-date>"


def test_feed_created_at_is_mandatory_and_feed_updated_at_is_optional() -> None:
    with pytest.raises(InvalidArgumentError):
        FeedCreatedAt(None)  # pyright: ignore[reportArgumentType]

    assert FeedUpdatedAt(None).value is None


@pytest.mark.parametrize(
    "value",
    [
        "CMS",
        "EL_PAIS",
        "EL_MUNDO",
        "EL_ESPANOL",
        "EL_CONFIDENCIAL",
        "LA_RAZON",
        "LA_VANGUARDIA",
    ],
)
def test_feed_source_keeps_a_known_source(value: str) -> None:
    assert FeedSource(value).value == value


@pytest.mark.parametrize(
    ("value", "rendered"),
    [("EL_PERIODICO", "EL_PERIODICO"), ("cms", "cms"), (1, "1"), (None, "None")],
)
def test_feed_source_rejects_an_unknown_source(value: object, rendered: str) -> None:
    with pytest.raises(InvalidArgumentError) as error:
        FeedSource(value)

    assert str(error.value) == f"<FeedSource> does not allow the value <{rendered}>"


@pytest.mark.parametrize(
    "value",
    [
        "POLITICS",
        "INTERNATIONAL",
        "ECONOMY",
        "SOCIETY",
        "SPORTS",
        "CULTURE",
        "TECHNOLOGY",
        "SCIENCE",
        "HEALTH",
        "OPINION",
        "OTHER",
    ],
)
def test_feed_category_keeps_a_known_category(value: str) -> None:
    assert FeedCategory(value).value == value


@pytest.mark.parametrize(
    ("value", "rendered"),
    [("WEATHER", "WEATHER"), ("sports", "sports"), ("", ""), (1, "1"), (None, "None")],
)
def test_feed_category_rejects_an_unknown_category(value: object, rendered: str) -> None:
    with pytest.raises(InvalidArgumentError) as error:
        FeedCategory(value)

    assert str(error.value) == f"<FeedCategory> does not allow the value <{rendered}>"


@pytest.mark.parametrize(
    "value",
    [
        "https://www.elmundo.es/espana/2026/10/20/noticia.html",
        "http://www.larazon.es/deportes/futbol/123.html",
        "https://www.lavanguardia.com/local/valencia/1.html?utm=home#comments",
        None,
    ],
)
def test_feed_url_keeps_an_absolute_http_url_or_null(value: str | None) -> None:
    assert FeedUrl(value).value == value


@pytest.mark.parametrize(
    "value",
    [
        "/deportes/futbol/123.html",
        "www.elmundo.es/espana/",
        "ftp://www.elmundo.es/espana/",
        "mailto:redaccion@elmundo.es",
        "https://",
        "",
        "   ",
        1,
    ],
)
def test_feed_url_rejects_a_value_that_is_not_an_absolute_http_url(value: object) -> None:
    with pytest.raises(InvalidArgumentError) as error:
        FeedUrl(value)  # pyright: ignore[reportArgumentType]

    assert str(error.value) == f"<FeedUrl> does not allow the value <{value}>"
