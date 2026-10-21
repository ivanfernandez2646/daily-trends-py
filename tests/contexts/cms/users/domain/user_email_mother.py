from daily_trends_py.contexts.cms.users.domain.value_objects import UserEmail
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class UserEmailMother:
    @staticmethod
    def create(value: str) -> UserEmail:
        return UserEmail(value)

    @staticmethod
    def random() -> UserEmail:
        return UserEmail(MotherCreator.email())
