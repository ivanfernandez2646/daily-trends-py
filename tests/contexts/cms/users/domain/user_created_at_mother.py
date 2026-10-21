from datetime import datetime

from daily_trends_py.contexts.cms.users.domain.value_objects import UserCreatedAt
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class UserCreatedAtMother:
    @staticmethod
    def create(value: datetime) -> UserCreatedAt:
        return UserCreatedAt(value)

    @staticmethod
    def random() -> UserCreatedAt:
        return UserCreatedAt(MotherCreator.date_time())
