import pytest
from pydantic import TypeAdapter, ValidationError

from daily_trends_py.apps.cms_backend.routes.feed_schemas import (
    CreateFeedRequest,
    UpdateFeedRequest,
)
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCategory

update_feed_request = TypeAdapter(UpdateFeedRequest)

NOT_STRINGS = [
    pytest.param(0, id="number"),
    pytest.param(True, id="boolean"),
    pytest.param([], id="list"),
    pytest.param({}, id="object"),
]


def _problems(error: ValidationError) -> list[tuple[tuple[int | str, ...], str]]:
    return [(problem["loc"], problem["msg"]) for problem in error.errors()]


def test_create_requires_title_author_and_category() -> None:
    with pytest.raises(ValidationError) as error:
        CreateFeedRequest.model_validate_json("{}")

    assert _problems(error.value) == [
        (("title",), "Field required"),
        (("author",), "Field required"),
        (("category",), "Field required"),
    ]


@pytest.mark.parametrize("field", ["title", "author", "description"])
@pytest.mark.parametrize("value", NOT_STRINGS)
def test_create_does_not_coerce_other_types_to_strings(field: str, value: object) -> None:
    body = {"title": "A title", "author": "Ivan", "category": "SPORTS", field: value}

    with pytest.raises(ValidationError) as error:
        CreateFeedRequest.model_validate(body)

    assert _problems(error.value) == [((field,), "Input should be a valid string")]


def test_create_accepts_a_null_or_absent_description() -> None:
    sent_null = CreateFeedRequest.model_validate_json(
        '{"title": "A title", "author": "Ivan", "category": "SPORTS", "description": null}'
    )
    absent = CreateFeedRequest.model_validate_json(
        '{"title": "A title", "author": "Ivan", "category": "SPORTS"}'
    )

    assert sent_null.description is None
    assert absent.description is None


def test_create_ignores_unknown_fields_and_the_url() -> None:
    request = CreateFeedRequest.model_validate_json(
        '{"title": "A title", "author": "Ivan", "category": "SPORTS", "source": "El Mundo",'
        ' "url": "https://www.elmundo.es/1.html"}'
    )

    assert request.model_dump() == {
        "title": "A title",
        "author": "Ivan",
        "category": FeedCategory.SPORTS,
        "description": None,
    }


def test_create_accepts_a_category_value_from_the_parsed_body() -> None:
    # The route validates the decoded JSON body, so the category arrives as a plain string.
    request = CreateFeedRequest.model_validate(
        {"title": "A title", "author": "Ivan", "category": "SPORTS"}
    )

    assert request.category is FeedCategory.SPORTS


@pytest.mark.parametrize(
    "category",
    [
        pytest.param(None, id="null"),
        pytest.param(1, id="number"),
        pytest.param("sports", id="lowercase"),
        pytest.param("WEATHER", id="unknown"),
        pytest.param("", id="empty"),
    ],
)
def test_create_rejects_a_category_that_is_not_a_known_value(category: object) -> None:
    with pytest.raises(ValidationError) as error:
        CreateFeedRequest.model_validate(
            {"title": "A title", "author": "Ivan", "category": category}
        )

    [(location, _)] = _problems(error.value)
    assert location == ("category",)


def test_update_keeps_only_the_fields_that_were_sent() -> None:
    assert update_feed_request.validate_json("{}") == {}
    assert update_feed_request.validate_json('{"description": null}') == {"description": None}
    assert update_feed_request.validate_json('{"title": "A title"}') == {"title": "A title"}
    assert update_feed_request.validate_python({"category": "SPORTS"}) == {
        "category": FeedCategory.SPORTS
    }


def test_update_rejects_a_null_title() -> None:
    with pytest.raises(ValidationError) as error:
        update_feed_request.validate_json('{"title": null}')

    assert _problems(error.value) == [(("title",), "Input should be a valid string")]


@pytest.mark.parametrize("field", ["title", "description"])
@pytest.mark.parametrize("value", NOT_STRINGS)
def test_update_does_not_coerce_other_types_to_strings(field: str, value: object) -> None:
    with pytest.raises(ValidationError) as error:
        update_feed_request.validate_python({field: value})

    assert _problems(error.value) == [((field,), "Input should be a valid string")]


@pytest.mark.parametrize("category", [None, "sports", "WEATHER", 1])
def test_update_rejects_a_category_that_is_not_a_known_value(category: object) -> None:
    with pytest.raises(ValidationError) as error:
        update_feed_request.validate_python({"category": category})

    [(location, _)] = _problems(error.value)
    assert location == ("category",)


def test_update_ignores_unknown_fields_and_the_url() -> None:
    assert update_feed_request.validate_json(
        '{"title": "A title", "author": "Ivan", "url": "https://www.elmundo.es/1.html"}'
    ) == {"title": "A title"}
