from collections.abc import Callable, Coroutine
from typing import Any

from dishka.integrations.fastapi import DishkaRoute
from fastapi import Request, Response
from starlette.types import Message

_EMPTY_JSON_OBJECT = b"{}"


class FeedRoute(DishkaRoute):
    """Injects dependencies from the container and reads a missing or empty body as `{}`.

    Without this, FastAPI answers a missing body as a whole instead of listing each required
    field, as it does for `{}`.
    """

    # `Any` comes from the signature FastAPI declares for this hook.
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            if await request.body():
                return await handler(request)
            return await handler(_with_an_empty_json_object(request))

        return handle


def _with_an_empty_json_object(request: Request) -> Request:
    headers = [(name, value) for name, value in request.scope["headers"] if name != b"content-type"]
    scope = {**request.scope, "headers": [*headers, (b"content-type", b"application/json")]}

    async def receive() -> Message:
        return {"type": "http.request", "body": _EMPTY_JSON_OBJECT, "more_body": False}

    return Request(scope, receive)
