from datetime import UTC, datetime
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
    def url() -> str:
        return f"{_faker.url(schemes=['https'])}{_faker.uri_path()}.html"

    @staticmethod
    def name() -> str:
        return _faker.name()

    @staticmethod
    def email() -> str:
        return _faker.email()

    @staticmethod
    def password() -> str:
        return _faker.password(length=16)

    @staticmethod
    def boolean() -> bool:
        return _faker.boolean()

    @staticmethod
    def date_time() -> datetime:
        """An aware UTC date-time with millisecond precision, as feeds store them."""
        date_time = _faker.date_time(tzinfo=UTC)
        return date_time.replace(microsecond=date_time.microsecond // 1000 * 1000)
