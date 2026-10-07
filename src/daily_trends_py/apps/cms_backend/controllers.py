from collections.abc import Awaitable, Callable, Sequence

from fastapi import Response, status
from fastapi.responses import JSONResponse

type ErrorMapping = tuple[type[Exception], int]


async def run_controller(
    action: Callable[[], Awaitable[Response]],
    exceptions: Sequence[ErrorMapping] = (),
) -> Response:
    """Run a route and map only the errors it declares; any other error is a 500."""
    try:
        return await action()
    except Exception as error:
        status_code = next(
            (code for error_type, code in exceptions if isinstance(error, error_type)),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        return JSONResponse({"error": str(error)}, status_code=status_code)
