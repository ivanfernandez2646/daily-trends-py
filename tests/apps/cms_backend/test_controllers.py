from collections.abc import Sequence

import httpx2
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from daily_trends_py.apps.cms_backend.controllers import ErrorMapping, run_controller
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)


class NotFoundError(Exception):
    pass


class AlreadyExistsError(Exception):
    pass


class SpecificInvalidArgumentError(InvalidArgumentError):
    pass


def app_raising(error: Exception, exceptions: Sequence[ErrorMapping]) -> FastAPI:
    app = FastAPI()

    async def fail() -> Response:
        raise error

    @app.get("/route")
    async def route() -> Response:  # pyright: ignore[reportUnusedFunction]
        return await run_controller(fail, exceptions)

    return app


def request(error: Exception, exceptions: Sequence[ErrorMapping] = ()) -> httpx2.Response:
    with TestClient(app_raising(error, exceptions), follow_redirects=False) as client:
        return client.get("/route")


def test_maps_declared_invalid_argument_error_to_400() -> None:
    response = request(InvalidArgumentError("bad"), [(InvalidArgumentError, 400)])

    assert response.status_code == 400
    assert response.content == b'{"error":"bad"}'


def test_maps_declared_not_found_error_to_404_keeping_angle_brackets() -> None:
    response = request(NotFoundError("Feed with id <x> not found"), [(NotFoundError, 404)])

    assert response.status_code == 404
    assert response.content == b'{"error":"Feed with id <x> not found"}'


def test_maps_declared_already_exists_error_to_302_without_location() -> None:
    response = request(
        AlreadyExistsError("Feed with id <x> already exists"), [(AlreadyExistsError, 302)]
    )

    assert response.status_code == 302
    assert response.content == b'{"error":"Feed with id <x> already exists"}'
    assert "location" not in response.headers


def test_maps_undeclared_error_to_500_with_its_message() -> None:
    response = request(InvalidArgumentError("bad"))

    assert response.status_code == 500
    assert response.content == b'{"error":"bad"}'


def test_uses_first_matching_mapping_when_several_match() -> None:
    response = request(
        SpecificInvalidArgumentError("bad"),
        [(InvalidArgumentError, 400), (SpecificInvalidArgumentError, 404)],
    )

    assert response.status_code == 400
