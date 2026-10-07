from datetime import UTC
from uuid import uuid4

from faker import Faker

_faker = Faker()


class MotherCreator:
    @staticmethod
    def uuid() -> str:
        return str(uuid4())

    @staticmethod
    def word() -> str:
        return _faker.word()

    @staticmethod
    def sentence() -> str:
        return _faker.sentence()

    @staticmethod
    def name() -> str:
        return _faker.name()

    @staticmethod
    def boolean() -> bool:
        return _faker.boolean()

    @staticmethod
    def iso_date_time() -> str:
        date_time = _faker.date_time(tzinfo=UTC)
        return date_time.isoformat(timespec="milliseconds").replace("+00:00", "Z")
