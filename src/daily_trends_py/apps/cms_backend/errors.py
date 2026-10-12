import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import cast

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from daily_trends_py.contexts.cms.shared.domain.conflict_error import ConflictError
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.not_found_error import NotFoundError

logger = logging.getLogger(__name__)

# Kinds, not concrete errors: a new domain error picks its status by inheriting from one.
_STATUS_BY_KIND: dict[type[Exception], int] = {
    InvalidArgumentError: status.HTTP_400_BAD_REQUEST,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
}


def error_response(
    status_code: int, message: str, headers: Mapping[str, str] | None = None
) -> Response:
    """The single error body of the API: `{"error": "<message>"}`."""
    return JSONResponse({"error": message}, status_code=status_code, headers=headers)


def register_error_handling(app: FastAPI) -> None:
    """Answer every error with `error_response`.

    Call it before adding CORS: the middleware that answers the 500 must sit inside CORS, so the
    500 gets the CORS headers like any other response.
    """
    app.add_middleware(UnhandledErrorMiddleware)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(HTTPException, _handle_http_exception)
    for kind, status_code in _STATUS_BY_KIND.items():
        app.add_exception_handler(kind, _answer_with(status_code))


class UnhandledErrorMiddleware:
    """Answers an error no handler maps with a 500, logged once and not raised again.

    FastAPI's own handler for `Exception` runs outside every middleware, CORS included, and
    raises the error again after answering, so the server logs it a second time.
    """

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        response_started = False

        async def send_tracking_start(message: Message) -> None:
            nonlocal response_started
            response_started = response_started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self._app(scope, receive, send_tracking_start)
        except Exception as error:
            logger.error("Unhandled error", exc_info=error)
            # Part of the response is already sent: only the server can end it.
            if response_started:
                raise
            response = error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, str(error))
            await response(scope, receive, send)


async def _handle_validation_error(_request: Request, error: Exception) -> Response:
    assert isinstance(error, RequestValidationError)
    problems = "; ".join(f"{_location(problem)}: {problem['msg']}" for problem in _problems(error))
    return error_response(status.HTTP_400_BAD_REQUEST, problems)


async def _handle_http_exception(_request: Request, error: Exception) -> Response:
    assert isinstance(error, HTTPException)
    return error_response(error.status_code, str(error.detail), error.headers)


def _problems(error: RequestValidationError) -> list[Mapping[str, object]]:
    return [cast(Mapping[str, object], problem) for problem in error.errors()]


def _location(problem: Mapping[str, object]) -> str:
    """The dotted path without the `body` prefix; a body that is not a JSON object is `body`."""
    location = [str(part) for part in cast(Sequence[object], problem["loc"])]
    # A malformed JSON body points at the character where parsing failed, not at a field.
    if problem["type"] == "json_invalid" or location == ["body"]:
        return "body"
    if location[0] == "body":
        location = location[1:]
    return ".".join(location)


def _answer_with(status_code: int) -> Callable[[Request, Exception], Awaitable[Response]]:
    async def handle(_request: Request, error: Exception) -> Response:
        return error_response(status_code, str(error))

    return handle
