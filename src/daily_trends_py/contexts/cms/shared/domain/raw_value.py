from enum import Enum
from typing import cast


class Missing(Enum):
    """A field absent from the input, as opposed to one sent as `null`."""

    MISSING = "MISSING"


MISSING = Missing.MISSING


def render_value(value: object) -> str:
    """Render a raw input value the way the API prints it inside error messages."""
    match value:
        case Missing.MISSING:
            return "undefined"
        case None:
            return "null"
        case bool():
            return "true" if value else "false"
        case float() if value.is_integer():
            return str(int(value))
        case str():
            return value
        case int() | float():
            return str(value)
        case list():
            items = cast(list[object], value)
            return ",".join("" if item is None else render_value(item) for item in items)
        case _:
            return "[object Object]"
