from daily_trends_py.contexts.cms.users.domain.value_objects import UserPasswordHash
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator


class UserPasswordHashMother:
    @staticmethod
    def create(value: str) -> UserPasswordHash:
        return UserPasswordHash(value)

    @staticmethod
    def random() -> UserPasswordHash:
        return UserPasswordHash(f"hashed:{MotherCreator.password()}")
