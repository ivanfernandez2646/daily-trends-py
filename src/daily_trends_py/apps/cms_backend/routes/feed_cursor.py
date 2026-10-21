import base64
import json
from datetime import datetime, timedelta
from typing import cast

from daily_trends_py.contexts.cms.feeds.domain.feed_position import FeedPosition
from daily_trends_py.contexts.cms.feeds.domain.value_objects import FeedCreatedAt, FeedId
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)


def encode_cursor(position: FeedPosition) -> str:
    """URL-safe base64 of `{"created_at", "id"}`, without padding: opaque to clients."""
    document = {
        "created_at": position.created_at.value.isoformat().replace("+00:00", "Z"),
        "id": position.id.value,
    }
    return base64.urlsafe_b64encode(json.dumps(document).encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> FeedPosition:
    """The position of `cursor`; raises `ValueError("Invalid cursor")` for any other value."""
    try:
        document: object = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        if not isinstance(document, dict):
            raise ValueError("not an object")
        fields = cast(dict[str, object], document)
        created_at, id = fields.get("created_at"), fields.get("id")
        if not isinstance(created_at, str) or not isinstance(id, str):
            raise ValueError("missing date or id")
        instant = datetime.fromisoformat(created_at)
        if instant.utcoffset() != timedelta(0):
            raise ValueError("not a UTC instant")
        return FeedPosition(created_at=FeedCreatedAt(instant), id=FeedId(id))
    # Bad base64, UTF-8 and JSON all raise a `ValueError`.
    except (ValueError, InvalidArgumentError) as error:
        raise ValueError("Invalid cursor") from error
