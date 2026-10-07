import json
from collections.abc import Mapping
from typing import cast
from urllib.parse import parse_qs

from fastapi import Request, status
from fastapi.responses import PlainTextResponse

_JSON_WHITESPACE = " \t\n\r"


class MalformedRequestBody(Exception):
    pass


async def parse_body(request: Request) -> Mapping[str, object]:
    """Read a JSON or urlencoded body into fields; any other body has no fields.

    A JSON body must start with an object or an array; an array has no fields.
    An urlencoded key sent more than once becomes a list of its values.
    """
    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    raw = await request.body()
    if not raw:
        return {}
    if media_type == "application/json":
        return _parse_json(raw)
    if media_type == "application/x-www-form-urlencoded":
        return _parse_urlencoded(raw)
    return {}


async def handle_malformed_request_body(_request: Request, _error: Exception) -> PlainTextResponse:
    return PlainTextResponse("Bad Request", status_code=status.HTTP_400_BAD_REQUEST)


def _parse_json(raw: bytes) -> Mapping[str, object]:
    try:
        text = raw.decode()
        body: object = json.loads(text)
    except ValueError as error:
        raise MalformedRequestBody from error
    if text.lstrip(_JSON_WHITESPACE)[:1] not in ("{", "["):
        raise MalformedRequestBody
    if not isinstance(body, dict):
        return {}
    return cast(Mapping[str, object], body)


def _parse_urlencoded(raw: bytes) -> Mapping[str, object]:
    fields = parse_qs(raw.decode(errors="replace"), keep_blank_values=True)
    return {key: values[0] if len(values) == 1 else values for key, values in fields.items()}
