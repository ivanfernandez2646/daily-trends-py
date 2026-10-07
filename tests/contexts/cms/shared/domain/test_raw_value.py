import pytest

from daily_trends_py.contexts.cms.shared.domain.raw_value import MISSING, render_value


@pytest.mark.parametrize(
    ("value", "rendered"),
    [
        (MISSING, "undefined"),
        (None, "null"),
        (True, "true"),
        (False, "false"),
        (0, "0"),
        (123, "123"),
        (1.0, "1"),
        (1.5, "1.5"),
        ("", ""),
        ("a title", "a title"),
        ([], ""),
        (["a", 1, None, True], "a,1,,true"),
        ([["a", "b"], "c"], "a,b,c"),
        ({"a": 1}, "[object Object]"),
    ],
)
def test_renders_raw_values_as_they_appear_in_error_messages(value: object, rendered: str) -> None:
    assert render_value(value) == rendered
