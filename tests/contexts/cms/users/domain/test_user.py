from datetime import UTC, datetime

from daily_trends_py.contexts.cms.users.domain.user import User
from tests.contexts.cms.users.domain.user_email_mother import UserEmailMother
from tests.contexts.cms.users.domain.user_id_mother import UserIdMother
from tests.contexts.cms.users.domain.user_mother import UserMother
from tests.contexts.cms.users.domain.user_password_hash_mother import UserPasswordHashMother

NOW = datetime(2026, 10, 21, 9, 30, tzinfo=UTC)


def test_create_keeps_the_fields_created_now_without_recording_events() -> None:
    id, email, password_hash = (
        UserIdMother.random(),
        UserEmailMother.random(),
        UserPasswordHashMother.random(),
    )

    user = User.create(id=id, email=email, password_hash=password_hash, now=NOW)

    assert (user.id, user.email, user.password_hash) == (id, email, password_hash)
    assert user.created_at.value == NOW
    assert user.pull_domain_events() == []


def test_primitives_round_trip() -> None:
    user = UserMother.random()

    assert User.from_primitives(user.to_primitives()).to_primitives() == user.to_primitives()
