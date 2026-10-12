import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response, status
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
    for kind, status_code in _STATUS_BY_KIND.items():
        app.add_exception_handler(kind, _answer_with(status_code))
    app.add_exception_handler(Exception, _handle_unexpected_error)


def _answer_with(status_code: int) -> Callable[[Request, Exception], Awaitable[Response]]:
    async def handle(_request: Request, error: Exception) -> Response:
        return _error_response(error, status_code)

    return handle


async def _handle_unexpected_error(_request: Request, error: Exception) -> Response:
    logger.error("Unhandled error", exc_info=error)
    return _error_response(error, status.HTTP_500_INTERNAL_SERVER_ERROR)


def _error_response(error: Exception, status_code: int) -> Response:
    return JSONResponse({"error": str(error)}, status_code=status_code)
