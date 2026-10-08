from daily_trends_py.contexts.cms.shared.domain.date_time_value_object import (
    DateTimeValueObject,
    RequiredDateTimeValueObject,
)
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class DateTimeValueObjectMother:
    @staticmethod
    def create(value: str | None) -> DateTimeValueObject:
        return DateTimeValueObject(value)

    @staticmethod
    def random() -> DateTimeValueObject:
        return DateTimeValueObject(
            MotherCreator.iso_date_time() if MotherCreator.boolean() else None
        )


class RequiredDateTimeValueObjectMother:
    @staticmethod
    def create(value: str) -> RequiredDateTimeValueObject:
        return RequiredDateTimeValueObject(value)

    @staticmethod
    def random() -> RequiredDateTimeValueObject:
        return RequiredDateTimeValueObject(MotherCreator.iso_date_time())

    @staticmethod
    def now() -> RequiredDateTimeValueObject:
        return RequiredDateTimeValueObject.now()
