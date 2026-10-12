import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import cast

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    for kind, status_code in _STATUS_BY_KIND.items():
        app.add_exception_handler(kind, _answer_with(status_code))
    app.add_exception_handler(Exception, _handle_unexpected_error)


async def _handle_validation_error(_request: Request, error: Exception) -> Response:
    assert isinstance(error, RequestValidationError)
    problems = "; ".join(f"{_location(problem)}: {problem['msg']}" for problem in _problems(error))
    return JSONResponse({"error": problems}, status_code=status.HTTP_400_BAD_REQUEST)


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
        return _error_response(error, status_code)

    return handle


async def _handle_unexpected_error(_request: Request, error: Exception) -> Response:
    logger.error("Unhandled error", exc_info=error)
    return _error_response(error, status.HTTP_500_INTERNAL_SERVER_ERROR)


def _error_response(error: Exception, status_code: int) -> Response:
    return JSONResponse({"error": str(error)}, status_code=status_code)
