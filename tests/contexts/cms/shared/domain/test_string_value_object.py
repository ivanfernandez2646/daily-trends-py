from dataclasses import dataclass

import pytest

from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.required_string_value_object import (
    RequiredStringValueObject,
)
from daily_trends_py.contexts.cms.shared.domain.string_value_object import StringValueObject
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


@dataclass(frozen=True)
class DummyString(StringValueObject):
    pass


@dataclass(frozen=True)
class DummyRequiredString(RequiredStringValueObject):
    pass


@pytest.mark.parametrize("value", [None, "", "  ", "a word"])
def test_string_value_object_accepts_any_string_or_none(value: str | None) -> None:
    assert DummyString(value).value == value


def test_string_value_objects_with_the_same_value_are_equal() -> None:
    value = MotherCreator.word()

    assert DummyString(value) == DummyString(value)


def test_string_value_objects_are_case_sensitive() -> None:
    assert DummyString("test") != DummyString("TEST")


@pytest.mark.parametrize("value", ["", "   "])
def test_required_string_rejects_empty_or_blank_values(value: str) -> None:
    with pytest.raises(InvalidArgumentError) as error:
        DummyRequiredString(value)

    assert str(error.value) == f"<DummyRequiredString> is mandatory. Current value: <{value}>"


def test_required_string_keeps_the_value_untrimmed() -> None:
    assert DummyRequiredString(" a ").value == " a "


def test_required_strings_with_the_same_value_are_equal() -> None:
    value = MotherCreator.word()

    assert DummyRequiredString(value) == DummyRequiredString(value)
    assert DummyRequiredString("test") != DummyRequiredString("TEST")
