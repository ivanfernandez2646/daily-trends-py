from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response

from daily_trends_py.apps.cms_backend.http.authentication import authenticate
from daily_trends_py.apps.cms_backend.http.json_body_route import JsonBodyRoute


class AdminRoute(JsonBodyRoute):
    """The route class for the routes only administrators can call.

    It authenticates before anything else runs, so a request without a valid token answers 401
    even when its body or id is invalid or its feed does not exist. A dependency would run too
    late: the body is read and parsed before dependencies are solved.
    """

    # `Any` comes from the signature FastAPI declares for this hook.
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            await authenticate(request)
            return await handler(request)

        return handle
