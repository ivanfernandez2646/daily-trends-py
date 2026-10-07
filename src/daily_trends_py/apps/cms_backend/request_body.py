from collections.abc import Mapping
from typing import cast

from fastapi import Request


async def parse_body(request: Request) -> Mapping[str, object]:
    """Read a JSON object body; another content type, an empty body or a non-object is `{}`."""
    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type != "application/json" or not await request.body():
        return {}
    body: object = await request.json()
    if not isinstance(body, dict):
        return {}
    return cast(Mapping[str, object], body)
