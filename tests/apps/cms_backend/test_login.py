import httpx2
import pytest
from dishka import AsyncContainer
from fastapi.testclient import TestClient

from daily_trends_py.apps.cms_backend.settings import Settings
from daily_trends_py.contexts.cms.users.application.create.user_creator import UserCreator
from daily_trends_py.contexts.cms.users.domain.access_token_verifier import AccessTokenVerifier
from daily_trends_py.contexts.cms.users.domain.value_objects import UserId
from tests.apps.cms_backend.conftest import resolve, run_in_app

pytestmark = pytest.mark.integration

PASSWORD = "a-long-enough-secret"


@pytest.fixture
def admin_id(client: TestClient, container: AsyncContainer) -> UserId:
    creator = resolve(client, container, UserCreator)
    user = run_in_app(client, lambda: creator.execute(email="Admin@Example.com", password=PASSWORD))
    return user.id


def login(client: TestClient, body: object) -> httpx2.Response:
    return client.post("/auth/login", json=body)


@pytest.mark.parametrize("email", ["admin@example.com", "Admin@Example.com"])
def test_valid_credentials_answer_a_bearer_token_for_the_admin(
    client: TestClient,
    container: AsyncContainer,
    settings: Settings,
    admin_id: UserId,
    email: str,
) -> None:
    response = login(client, {"email": email, "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "token_type", "expires_in"}
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.auth_token_ttl_seconds
    verifier = resolve(client, container, AccessTokenVerifier)
    assert verifier.verify(body["access_token"]).user_id == admin_id


@pytest.mark.parametrize(
    "credentials",
    [
        pytest.param({"email": "admin@example.com", "password": "a-wrong-password"}, id="wrong"),
        pytest.param({"email": "someone@example.com", "password": PASSWORD}, id="unknown"),
        pytest.param({"email": "not-an-email", "password": PASSWORD}, id="invalid email"),
        pytest.param({"email": "admin@example.com", "password": ""}, id="empty password"),
    ],
)
@pytest.mark.usefixtures("admin_id")
def test_wrong_credentials_answer_the_same_401(
    client: TestClient, credentials: dict[str, str]
) -> None:
    response = login(client, credentials)

    assert response.status_code == 401
    assert response.json() == {"error": "Invalid email or password"}
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    ("body", "error"),
    [
        pytest.param({"email": "a@b.co"}, "password: Field required", id="missing password"),
        pytest.param(
            {"email": "a@b.co", "password": 123456789012},
            "password: Input should be a valid string",
            id="password not a string",
        ),
        pytest.param(
            {"password": PASSWORD},
            "email: Field required",
            id="missing email",
        ),
    ],
)
def test_an_invalid_body_answers_400(client: TestClient, body: object, error: str) -> None:
    response = login(client, body)

    assert response.status_code == 400
    assert response.json() == {"error": error}


def test_a_body_that_is_not_json_answers_400(client: TestClient) -> None:
    response = client.post(
        "/auth/login", content=b"{not json", headers={"content-type": "application/json"}
    )

    assert response.status_code == 400
    assert response.json()["error"].startswith("body: ")
