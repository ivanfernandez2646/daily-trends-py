from typing import Annotated

import httpx2
import pytest
from fastapi import Depends, FastAPI, Response
from fastapi.testclient import TestClient
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from daily_trends_py.apps.cms_backend.errors import register_error_handling
from daily_trends_py.contexts.cms.shared.domain.conflict_error import ConflictError
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.not_found_error import NotFoundError


class SomethingInvalid(InvalidArgumentError):
    pass


class SomethingNotFound(NotFoundError):
    pass


class SomethingConflicting(ConflictError):
    pass


class SomethingOfNoKind(Exception):
    pass


def request(error: Exception) -> httpx2.Response:
    app = FastAPI()
    register_error_handling(app)

    @app.get("/route")
    async def route() -> Response:  # pyright: ignore[reportUnusedFunction]
        raise error

    # Not told to ignore server errors: a 500 the app answered must not be raised again.
    with TestClient(app) as client:
        return client.get("/route")


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        pytest.param(SomethingInvalid("Invalid <x>"), 400, id="invalid argument"),
        pytest.param(SomethingNotFound("Missing <x>"), 404, id="not found"),
        pytest.param(SomethingConflicting("Clash <x>"), 409, id="conflict"),
    ],
)
def test_maps_each_kind_of_domain_error_to_its_status(error: Exception, status_code: int) -> None:
    response = request(error)

    assert response.status_code == status_code
    assert response.json() == {"error": str(error)}


def test_a_conflict_answers_without_location() -> None:
    response = request(SomethingConflicting("Clash <x>"))

    assert "location" not in response.headers


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(SomethingOfNoKind("boom"), id="error of no kind"),
        pytest.param(ValueError("boom"), id="unexpected error"),
    ],
)
def test_an_error_of_no_kind_answers_a_generic_500_and_logs_the_error_with_method_and_path(
    error: Exception, caplog: pytest.LogCaptureFixture
) -> None:
    response = request(error)

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"error": "Internal server error"}
    [record] = [record for record in caplog.records if record.exc_info]
    assert record.levelname == "ERROR"
    assert record.getMessage() == "Unhandled error on GET /route"
    assert record.exc_info is not None and record.exc_info[1] is error
    assert "boom" in caplog.text
    assert "Traceback" in caplog.text


class Body(BaseModel):
    title: str
    author: str


def send(content: str, content_type: str = "application/json") -> httpx2.Response:
    app = FastAPI()
    register_error_handling(app)

    @app.put("/route")
    async def route(_body: Body) -> Response:  # pyright: ignore[reportUnusedFunction]
        return Response()

    with TestClient(app) as client:
        return client.put("/route", content=content, headers={"content-type": content_type})


def test_a_validation_error_answers_400_listing_each_problem_by_field() -> None:
    response = send('{"author": 0}')

    assert response.status_code == 400
    assert response.json() == {
        "error": "title: Field required; author: Input should be a valid string"
    }


@pytest.mark.parametrize(
    ("content", "content_type", "reason"),
    [
        pytest.param("{", "application/json", "JSON decode error", id="malformed JSON"),
        pytest.param(
            "[]",
            "application/json",
            "Input should be a valid dictionary or object to extract fields from",
            id="not an object",
        ),
    ],
)
def test_a_body_that_is_not_a_json_object_is_reported_at_body(
    content: str, content_type: str, reason: str
) -> None:
    response = send(content, content_type)

    assert response.status_code == 400
    assert response.json() == {"error": f"body: {reason}"}


def test_an_error_raised_by_a_dependency_is_mapped_too() -> None:
    async def failing_dependency() -> str:
        raise SomethingNotFound("Missing <x>")

    app = FastAPI()
    register_error_handling(app)

    @app.get("/route")
    async def route(  # pyright: ignore[reportUnusedFunction]
        _value: Annotated[str, Depends(failing_dependency)],
    ) -> Response:
        return Response()

    with TestClient(app) as client:
        response = client.get("/route")

    assert response.status_code == 404
    assert response.json() == {"error": "Missing <x>"}


def test_errors_the_framework_raises_use_the_same_body() -> None:
    app = FastAPI()
    register_error_handling(app)

    @app.get("/route")
    async def route() -> Response:  # pyright: ignore[reportUnusedFunction]
        return Response()

    with TestClient(app) as client:
        unknown_route = client.get("/unknown")
        wrong_method = client.post("/route")

    assert (unknown_route.status_code, unknown_route.json()) == (404, {"error": "Not Found"})
    assert (wrong_method.status_code, wrong_method.json()) == (
        405,
        {"error": "Method Not Allowed"},
    )
    assert wrong_method.headers["allow"] == "GET"


def test_a_framework_error_with_a_5xx_status_answers_the_generic_body() -> None:
    response = request(HTTPException(503, "Pool for mongo:27017 is exhausted"))

    assert response.status_code == 503
    assert response.json() == {"error": "Internal server error"}
