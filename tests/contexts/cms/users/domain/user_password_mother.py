from daily_trends_py.contexts.cms.users.domain.value_objects import UserPassword
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class UserPasswordMother:
    @staticmethod
    def create(value: str) -> UserPassword:
        return UserPassword(value)

    @staticmethod
    def random() -> UserPassword:
        return UserPassword(MotherCreator.password())
