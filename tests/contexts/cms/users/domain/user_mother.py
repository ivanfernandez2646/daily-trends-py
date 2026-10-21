from daily_trends_py.contexts.cms.users.domain.user import User
from daily_trends_py.contexts.cms.users.domain.value_objects import (
    UserCreatedAt,
    UserEmail,
    UserId,
    UserPasswordHash,
)
from tests.contexts.cms.users.domain.user_created_at_mother import UserCreatedAtMother
from tests.contexts.cms.users.domain.user_email_mother import UserEmailMother
from tests.contexts.cms.users.domain.user_id_mother import UserIdMother
from tests.contexts.cms.users.domain.user_password_hash_mother import UserPasswordHashMother


class UserMother:
    @staticmethod
    def random(
        *,
        id: UserId | None = None,
        email: UserEmail | None = None,
        password_hash: UserPasswordHash | None = None,
        created_at: UserCreatedAt | None = None,
    ) -> User:
        return User(
            id=id or UserIdMother.random(),
            email=email or UserEmailMother.random(),
            password_hash=password_hash or UserPasswordHashMother.random(),
            created_at=created_at or UserCreatedAtMother.random(),
        )
