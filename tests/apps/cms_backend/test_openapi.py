from importlib.metadata import version
from typing import cast

import pytest

from daily_trends_py.apps.cms_backend.container import create_container
from daily_trends_py.apps.cms_backend.main import create_app
from tests.apps.cms_backend.isolated_settings import IsolatedSettings
from tests.mongo import TEST_MONGO_URL

type Json = dict[str, object]


@pytest.fixture(scope="module")
def document() -> Json:
    # Generating the document needs no running app, so no database either.
    return create_app(create_container(IsolatedSettings(mongo_url=TEST_MONGO_URL))).openapi()


def _get(json: object, *path: str) -> object:
    for key in path:
        json = cast(Json, json)[key]
    return json


def _ref(name: str) -> Json:
    return {"$ref": f"#/components/schemas/{name}"}


def _response_schema(document: Json, path: str, method: str, status: str) -> object:
    return _get(
        document,
        "paths",
        path,
        method,
        "responses",
        status,
        "content",
        "application/json",
        "schema",
    )


def test_describes_the_api(document: Json) -> None:
    info = cast(Json, document["info"])

    assert info["title"] == "Daily trends"
    assert info["version"] == version("daily-trends-py")
    assert "scraped when the API starts and then every 2 hours" in cast(str, info["description"])


def test_lists_every_route(document: Json) -> None:
    paths = cast(dict[str, Json], document["paths"])

    assert {path: sorted(methods) for path, methods in paths.items()} == {
        "/status": ["get"],
        "/auth/login": ["post"],
        "/auth/me": ["get"],
        "/feed/list": ["get"],
        "/feed/scrap": ["get"],
        "/feed/home": ["get"],
        "/feed/{id}": ["delete", "get", "patch", "put"],
    }


@pytest.mark.parametrize(
    ("method", "schema"), [("put", "CreateFeedRequest"), ("patch", "UpdateFeedRequest")]
)
def test_describes_the_request_bodies(document: Json, method: str, schema: str) -> None:
    body = _get(
        document,
        "paths",
        "/feed/{id}",
        method,
        "requestBody",
        "content",
        "application/json",
        "schema",
    )

    assert body == _ref(schema)


@pytest.mark.parametrize(
    ("path", "method", "status"),
    [("/feed/{id}", "put", "201"), ("/feed/{id}", "get", "200"), ("/feed/{id}", "patch", "200")],
)
def test_a_feed_answers_with_the_feed_response(
    document: Json, path: str, method: str, status: str
) -> None:
    assert _response_schema(document, path, method, status) == _ref("FeedResponse")


@pytest.mark.parametrize("path", ["/feed/home", "/feed/scrap"])
def test_a_list_answers_with_feed_responses(document: Json, path: str) -> None:
    schema = cast(Json, _response_schema(document, path, "get", "200"))

    assert schema["type"] == "array"
    assert schema["items"] == _ref("FeedResponse")


def test_delete_answers_204_without_content(document: Json) -> None:
    response = cast(Json, _get(document, "paths", "/feed/{id}", "delete", "responses", "204"))

    assert "content" not in response


def test_the_feed_response_lists_its_fields_in_order_with_dates(document: Json) -> None:
    schema = cast(Json, _get(document, "components", "schemas", "FeedResponse"))
    properties = cast(dict[str, Json], schema["properties"])

    assert list(properties) == [
        "id",
        "title",
        "description",
        "author",
        "source",
        "category",
        "url",
        "created_at",
        "updated_at",
    ]
    assert properties["created_at"]["format"] == "date-time"
    assert properties["category"] == _ref("FeedCategory")
    assert properties["url"]["anyOf"] == [{"type": "string"}, {"type": "null"}]
    assert "url" in cast(list[str], schema["required"])


@pytest.mark.parametrize(
    ("path", "method", "statuses"),
    [
        ("/feed/{id}", "put", {"400", "401", "409", "500"}),
        ("/feed/{id}", "get", {"400", "404", "500"}),
        ("/feed/{id}", "patch", {"400", "401", "404", "500"}),
        ("/feed/{id}", "delete", {"400", "401", "404", "500"}),
        ("/feed/list", "get", {"400", "500"}),
        ("/feed/home", "get", {"500"}),
        ("/feed/scrap", "get", {"401", "500"}),
    ],
)
def test_declares_the_error_responses_of_each_feed_route(
    document: Json, path: str, method: str, statuses: set[str]
) -> None:
    responses = cast(Json, _get(document, "paths", path, method, "responses"))
    errors = {status for status in responses if status.startswith(("4", "5"))}

    assert errors == statuses
    for status in statuses:
        assert _response_schema(document, path, method, status) == _ref("ErrorResponse")


def test_does_not_advertise_fastapi_validation_errors(document: Json) -> None:
    paths = cast(dict[str, dict[str, Json]], document["paths"])
    schemas = cast(Json, _get(document, "components", "schemas"))

    assert all(
        "422" not in cast(Json, operation["responses"])
        for methods in paths.values()
        for operation in methods.values()
    )
    assert "HTTPValidationError" not in schemas
    assert "ValidationError" not in schemas


def test_the_feed_source_lists_every_source(document: Json) -> None:
    schema = cast(Json, _get(document, "components", "schemas", "FeedSource"))

    assert schema["enum"] == [
        "CMS",
        "EL_PAIS",
        "EL_MUNDO",
        "EL_ESPANOL",
        "EL_CONFIDENCIAL",
        "LA_RAZON",
        "LA_VANGUARDIA",
    ]


def test_the_front_page_describes_its_per_source_and_per_category_selection(
    document: Json,
) -> None:
    description = " ".join(
        cast(str, _get(document, "paths", "/feed/home", "get", "description")).split()
    )

    assert "at most 2 per source and 2 per category" in description
    assert "refresh" not in description


def test_the_manual_scraping_says_it_waits_for_a_run_in_progress(document: Json) -> None:
    description = cast(str, _get(document, "paths", "/feed/scrap", "get", "description"))

    assert "waits for a scraping run in progress" in description


def test_the_feed_category_lists_every_category(document: Json) -> None:
    schema = cast(Json, _get(document, "components", "schemas", "FeedCategory"))

    assert schema["enum"] == [
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
    ]


@pytest.mark.parametrize(
    ("schema", "required"), [("CreateFeedRequest", True), ("UpdateFeedRequest", False)]
)
def test_the_request_bodies_take_a_category(document: Json, schema: str, required: bool) -> None:
    body = cast(Json, _get(document, "components", "schemas", schema))
    properties = cast(Json, body["properties"])

    assert properties["category"] == _ref("FeedCategory")
    assert ("category" in cast(list[str], body.get("required", []))) is required
    assert "url" not in properties


def test_the_list_answers_a_page_of_feed_responses_newest_first(document: Json) -> None:
    page = cast(Json, _get(document, "components", "schemas", "FeedPageResponse"))

    assert _response_schema(document, "/feed/list", "get", "200") == _ref("FeedPageResponse")
    assert _get(page, "properties", "items") == {
        "items": _ref("FeedResponse"),
        "type": "array",
        "title": "Items",
    }
    assert cast(Json, _get(page, "properties", "next_cursor"))["anyOf"] == [
        {"type": "string"},
        {"type": "null"},
    ]
    assert page["required"] == ["items", "next_cursor"]
    assert "newest first" in cast(str, _get(document, "paths", "/feed/list", "get", "description"))


def test_the_list_takes_optional_query_parameters_with_their_bounds_and_values(
    document: Json,
) -> None:
    parameters = {
        cast(str, parameter["name"]): parameter
        for parameter in cast(
            list[Json], _get(document, "paths", "/feed/list", "get", "parameters")
        )
    }

    assert list(parameters) == ["limit", "category", "source", "q", "cursor"]
    assert all((p["in"], p["required"]) == ("query", False) for p in parameters.values())
    limit = cast(Json, parameters["limit"]["schema"])
    assert (limit["type"], limit["minimum"], limit["maximum"], limit["default"]) == (
        "integer",
        1,
        100,
        20,
    )
    assert cast(Json, parameters["category"]["schema"])["anyOf"] == [
        _ref("FeedCategory"),
        {"type": "null"},
    ]
    assert cast(Json, parameters["source"]["schema"])["anyOf"] == [
        _ref("FeedSource"),
        {"type": "null"},
    ]
    assert cast(Json, parameters["q"]["schema"])["anyOf"] == [
        {"type": "string", "maxLength": 100},
        {"type": "null"},
    ]
    assert "any of them" in cast(str, parameters["q"]["description"])
    assert cast(Json, parameters["cursor"]["schema"])["anyOf"] == [
        {"type": "string"},
        {"type": "null"},
    ]


def test_documents_the_login_under_the_auth_tag(document: Json) -> None:
    operation = cast(Json, _get(document, "paths", "/auth/login", "post"))
    responses = cast(Json, operation["responses"])

    assert operation["tags"] == ["auth"]
    assert _get(operation, "requestBody", "content", "application/json", "schema") == _ref(
        "LoginRequest"
    )
    assert _response_schema(document, "/auth/login", "post", "200") == _ref("AccessTokenResponse")
    assert {status for status in responses if status.startswith(("4", "5"))} == {
        "400",
        "401",
        "500",
    }
    for status in ("400", "401", "500"):
        assert _response_schema(document, "/auth/login", "post", status) == _ref("ErrorResponse")


def test_the_access_token_response_lists_its_fields(document: Json) -> None:
    schema = cast(Json, _get(document, "components", "schemas", "AccessTokenResponse"))
    properties = cast(dict[str, Json], schema["properties"])

    assert list(properties) == ["access_token", "token_type", "expires_in"]
    assert properties["token_type"]["const"] == "bearer"


def test_documents_the_admin_session_under_the_auth_tag(document: Json) -> None:
    operation = cast(Json, _get(document, "paths", "/auth/me", "get"))
    responses = cast(Json, operation["responses"])

    assert operation["tags"] == ["auth"]
    assert _response_schema(document, "/auth/me", "get", "200") == _ref("AdminSessionResponse")
    assert {status for status in responses if status.startswith(("4", "5"))} == {"401", "500"}
    for status in ("401", "500"):
        assert _response_schema(document, "/auth/me", "get", status) == _ref("ErrorResponse")


def test_the_admin_session_response_lists_its_fields_with_dates(document: Json) -> None:
    schema = cast(Json, _get(document, "components", "schemas", "AdminSessionResponse"))
    properties = cast(dict[str, Json], schema["properties"])

    assert list(properties) == ["id", "email", "created_at", "token_expires_at"]
    assert properties["created_at"]["format"] == "date-time"
    assert properties["token_expires_at"]["format"] == "date-time"


PROTECTED_OPERATIONS = {
    ("/feed/{id}", "put"),
    ("/feed/{id}", "patch"),
    ("/feed/{id}", "delete"),
    ("/feed/scrap", "get"),
    ("/auth/me", "get"),
}


def test_declares_a_bearer_security_scheme(document: Json) -> None:
    schemes = cast(Json, _get(document, "components", "securitySchemes"))

    assert schemes == {"bearer": {"type": "http", "scheme": "bearer"}}


def test_requires_the_bearer_token_on_exactly_the_protected_operations(document: Json) -> None:
    paths = cast(dict[str, dict[str, Json]], document["paths"])

    secured = {
        (path, method)
        for path, operations in paths.items()
        for method, operation in operations.items()
        if "security" in operation
    }

    assert secured == PROTECTED_OPERATIONS
    for path, method in PROTECTED_OPERATIONS:
        assert _get(document, "paths", path, method, "security") == [{"bearer": []}]
