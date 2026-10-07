from dataclasses import dataclass

import pytest

from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.raw_value import MISSING
from daily_trends_py.contexts.cms.shared.domain.uuid_value_object import UuidValueObject
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


@dataclass(frozen=True)
class DummyId(UuidValueObject):
    pass


@pytest.mark.parametrize(
    "value",
    [
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",  # v1
        "000003e8-1d4b-21ef-8000-325096b39f47",  # v2
        "6fa459ea-ee8a-3ca4-894e-db77e160355e",  # v3
        "04deff28-6c34-4634-a7c8-a4a09dabd87a",  # v4
        "886313e1-3b8a-5372-9b90-0c9aee199e5d",  # v5
        "00000000-0000-0000-0000-000000000000",  # nil
        "04DEFF28-6C34-4634-A7C8-A4A09DABD87A",
    ],
)
def test_accepts_uuids_from_version_1_to_5_and_nil(value: str) -> None:
    assert DummyId(value).value == value


@pytest.mark.parametrize(
    "value",
    [
        "not-a-uuid",
        "",
        "01890a5d-ac96-774b-bcce-b302099a8057",  # v7
        "04deff28-6c34-4634-c7c8-a4a09dabd87a",  # wrong variant
        "04deff28-6c34-4634-a7c8-a4a09dabd87a\n",
    ],
)
def test_rejects_values_that_are_not_valid_uuids(value: str) -> None:
    with pytest.raises(InvalidArgumentError) as error:
        DummyId(value)

    assert str(error.value) == f"<DummyId> does not allow the value <{value}>"


def test_random_creates_a_valid_uuid() -> None:
    assert DummyId(DummyId.random().value)


def test_uuids_with_the_same_value_are_equal() -> None:
    value = MotherCreator.uuid()

    assert DummyId(value) == DummyId(value)
    assert DummyId(value) != DummyId(MotherCreator.uuid())


def test_from_raw_accepts_a_valid_uuid() -> None:
    value = MotherCreator.uuid()

    assert DummyId.from_raw(value) == DummyId(value)


@pytest.mark.parametrize(("value", "rendered"), [(MISSING, "undefined"), (None, "null"), (1, "1")])
def test_from_raw_rejects_non_string_values(value: object, rendered: str) -> None:
    with pytest.raises(InvalidArgumentError) as error:
        DummyId.from_raw(value)

    assert str(error.value) == f"<DummyId> does not allow the value <{rendered}>"
