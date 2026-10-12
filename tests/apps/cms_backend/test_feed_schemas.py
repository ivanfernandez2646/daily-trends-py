import pytest
from pydantic import TypeAdapter, ValidationError

from daily_trends_py.apps.cms_backend.routes.feed_schemas import (
    CreateFeedRequest,
    UpdateFeedRequest,
)

update_feed_request = TypeAdapter(UpdateFeedRequest)

NOT_STRINGS = [
    pytest.param(0, id="number"),
    pytest.param(True, id="boolean"),
    pytest.param([], id="list"),
    pytest.param({}, id="object"),
]


def _problems(error: ValidationError) -> list[tuple[tuple[int | str, ...], str]]:
    return [(problem["loc"], problem["msg"]) for problem in error.errors()]


def test_create_requires_title_and_author() -> None:
    with pytest.raises(ValidationError) as error:
        CreateFeedRequest.model_validate_json("{}")

    assert _problems(error.value) == [
        (("title",), "Field required"),
        (("author",), "Field required"),
    ]


@pytest.mark.parametrize("field", ["title", "author", "description"])
@pytest.mark.parametrize("value", NOT_STRINGS)
def test_create_does_not_coerce_other_types_to_strings(field: str, value: object) -> None:
    body = {"title": "A title", "author": "Ivan", field: value}

    with pytest.raises(ValidationError) as error:
        CreateFeedRequest.model_validate(body)

    assert _problems(error.value) == [((field,), "Input should be a valid string")]


def test_create_accepts_a_null_or_absent_description() -> None:
    sent_null = CreateFeedRequest.model_validate_json(
        '{"title": "A title", "author": "Ivan", "description": null}'
    )
    absent = CreateFeedRequest.model_validate_json('{"title": "A title", "author": "Ivan"}')

    assert sent_null.description is None
    assert absent.description is None


def test_create_ignores_unknown_fields() -> None:
    request = CreateFeedRequest.model_validate_json(
        '{"title": "A title", "author": "Ivan", "source": "El Mundo"}'
    )

    assert request.model_dump() == {"title": "A title", "author": "Ivan", "description": None}


def test_update_keeps_only_the_fields_that_were_sent() -> None:
    assert update_feed_request.validate_json("{}") == {}
    assert update_feed_request.validate_json('{"description": null}') == {"description": None}
    assert update_feed_request.validate_json('{"title": "A title"}') == {"title": "A title"}


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


def test_update_ignores_unknown_fields() -> None:
    assert update_feed_request.validate_json('{"title": "A title", "author": "Ivan"}') == {
        "title": "A title"
    }
