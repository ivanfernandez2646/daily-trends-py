from datetime import UTC, datetime, timedelta

import pytest
from dishka import AsyncContainer
from fastapi.testclient import TestClient

from daily_trends_py.apps.cms_backend.settings import Settings
from daily_trends_py.contexts.cms.users.domain.access_token_issuer import AccessTokenIssuer
from daily_trends_py.contexts.cms.users.domain.user import User
from daily_trends_py.contexts.cms.users.domain.user_repository import UserRepository
from daily_trends_py.contexts.cms.users.infrastructure.tokens.jwt_access_tokens import (
    JwtAccessTokens,
)
from tests.apps.cms_backend.conftest import resolve, resolve_mongo_client, run_in_app
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator
from tests.contexts.cms.shared.fakes.fixed_clock import FixedClock
from tests.contexts.cms.users.domain.user_created_at_mother import UserCreatedAtMother
from tests.contexts.cms.users.domain.user_email_mother import UserEmailMother
from tests.contexts.cms.users.domain.user_mother import UserMother

pytestmark = pytest.mark.integration


@pytest.fixture
def admin(client: TestClient, container: AsyncContainer) -> User:
    user = UserMother.random(
        email=UserEmailMother.create("admin@example.com"),
        created_at=UserCreatedAtMother.create(datetime(2026, 10, 21, 8, 0, 0, tzinfo=UTC)),
    )
    repository = resolve(client, container, UserRepository)
    run_in_app(client, lambda: repository.create(user))
    return user


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_answers_the_administrator_and_when_the_token_expires(
    client: TestClient, settings: Settings, admin: User
) -> None:
    issued_at = datetime.now(UTC).replace(microsecond=0)
    ttl = timedelta(seconds=settings.auth_token_ttl_seconds)
    key = settings.auth_secret_key.get_secret_value()
    token = JwtAccessTokens(key, ttl, FixedClock(issued_at)).issue(admin.id).value

    response = client.get("/auth/me", headers=bearer(token))

    assert response.status_code == 200
    assert response.json() == {
        "id": admin.id.value,
        "email": "admin@example.com",
        "created_at": "2026-10-21T08:00:00Z",
        "token_expires_at": (issued_at + ttl).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def test_a_token_whose_user_was_deleted_answers_401_but_still_writes(
    client: TestClient, container: AsyncContainer, admin: User
) -> None:
    issuer = resolve(client, container, AccessTokenIssuer)
    headers = bearer(issuer.issue(admin.id).value)
    users = resolve_mongo_client(client, container).get_default_database()["users"]
    run_in_app(client, lambda: users.delete_one({"_id": admin.id.value}))

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"error": "Invalid or expired access token"}
    assert response.headers["www-authenticate"] == "Bearer"
    # The write routes never read the stored users, so the token is valid there until it expires.
    assert client.delete(f"/feed/{MotherCreator.uuid()}", headers=headers).status_code == 404
