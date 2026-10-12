from collections.abc import Callable, Coroutine
from typing import Any

from dishka.integrations.fastapi import DishkaRoute
from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.types import Message

JSON = "application/json"
_EMPTY_JSON_OBJECT = b"{}"


class JsonBodyRoute(DishkaRoute):
    """The route class for every router of the app: injects dependencies from the container and
    applies the body rules to the routes that declare a body.

    - A missing or empty body reads as `{}`, so validation lists each required field instead of
      answering the whole body as missing.
    - Any other content type than `application/json` is rejected, including the
      `application/*+json` types FastAPI would otherwise parse.
    """

    # `Any` comes from the signature FastAPI declares for this hook.
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()
        if self.body_field is None:
            return handler

        async def handle(request: Request) -> Response:
            if not await request.body():
                return await handler(_with_an_empty_json_object(request))
            if _media_type(request) != JSON:
                raise _wrong_content_type()
            return await handler(request)

        return handle


def _media_type(request: Request) -> str:
    return request.headers.get("content-type", "").split(";")[0].strip().lower()


def _wrong_content_type() -> RequestValidationError:
    return RequestValidationError(
        [
            {
                "type": "content_type",
                "loc": ("body",),
                "msg": f"Content type should be {JSON}",
                "input": None,
            }
        ]
    )


def _with_an_empty_json_object(request: Request) -> Request:
    headers = [(name, value) for name, value in request.scope["headers"] if name != b"content-type"]
    scope = {**request.scope, "headers": [*headers, (b"content-type", JSON.encode())]}

    async def receive() -> Message:
        return {"type": "http.request", "body": _EMPTY_JSON_OBJECT, "more_body": False}

    return Request(scope, receive)
