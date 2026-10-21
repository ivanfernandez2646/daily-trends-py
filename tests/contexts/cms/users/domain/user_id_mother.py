from daily_trends_py.contexts.cms.users.domain.value_objects import UserId
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class UserIdMother:
    @staticmethod
    def create(value: str) -> UserId:
        return UserId(value)

    @staticmethod
    def random() -> UserId:
        return UserId(MotherCreator.uuid())
