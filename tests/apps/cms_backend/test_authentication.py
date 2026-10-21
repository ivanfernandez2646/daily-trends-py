from datetime import UTC, datetime, timedelta

import httpx2
import pytest
from fastapi.testclient import TestClient

from daily_trends_py.apps.cms_backend.settings import Settings
from daily_trends_py.contexts.cms.users.infrastructure.tokens.jwt_access_tokens import (
    JwtAccessTokens,
)
from tests.contexts.cms.shared.domain.mother_creator import MotherCreator
from tests.contexts.cms.shared.fakes.fixed_clock import FixedClock
from tests.contexts.cms.users.domain.user_id_mother import UserIdMother
from tests.scrape_fixtures import FrontPagesTransport

pytestmark = pytest.mark.integration

FEED = {"title": "A title", "author": "Ivan", "category": "OTHER"}
PROTECTED = [
    pytest.param("PUT", "/feed/{id}", FEED, id="PUT /feed/{id}"),
    pytest.param("PATCH", "/feed/{id}", {"title": "Another title"}, id="PATCH /feed/{id}"),
    pytest.param("DELETE", "/feed/{id}", None, id="DELETE /feed/{id}"),
    pytest.param("GET", "/feed/scrap", None, id="GET /feed/scrap"),
    pytest.param("GET", "/auth/me", None, id="GET /auth/me"),
]
AUTHENTICATION_REQUIRED = {"error": "Authentication required"}
INVALID_TOKEN = {"error": "Invalid or expired access token"}


def send(
    client: TestClient,
    method: str,
    path: str,
    body: object,
    headers: dict[str, str] | None = None,
) -> httpx2.Response:
    return client.request(method, path.format(id=MotherCreator.uuid()), json=body, headers=headers)


def token_signed_with(key: str, *, issued_at: datetime, ttl: timedelta) -> str:
    return JwtAccessTokens(key, ttl, FixedClock(issued_at)).issue(UserIdMother.random()).value


def assert_unauthorized(response: httpx2.Response, body: dict[str, str]) -> None:
    assert response.status_code == 401
    assert response.json() == body
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(("method", "path", "body"), PROTECTED)
def test_a_protected_route_requires_a_token(
    anonymous_client: TestClient, method: str, path: str, body: object
) -> None:
    assert_unauthorized(send(anonymous_client, method, path, body), AUTHENTICATION_REQUIRED)


@pytest.mark.parametrize(
    "authorization",
    [
        pytest.param("", id="empty"),
        pytest.param("Bearer", id="bearer without a token"),
        pytest.param("Bearer ", id="bearer with a blank token"),
        pytest.param("Basic YWRtaW46c2VjcmV0", id="basic"),
        pytest.param("Token abc", id="another scheme"),
    ],
)
@pytest.mark.parametrize(("method", "path", "body"), PROTECTED)
def test_a_protected_route_requires_a_bearer_token(
    anonymous_client: TestClient, method: str, path: str, body: object, authorization: str
) -> None:
    response = send(anonymous_client, method, path, body, {"Authorization": authorization})

    assert_unauthorized(response, AUTHENTICATION_REQUIRED)


@pytest.mark.parametrize(("method", "path", "body"), PROTECTED)
def test_a_protected_route_rejects_a_token_signed_with_another_key(
    anonymous_client: TestClient, method: str, path: str, body: object
) -> None:
    token = token_signed_with(
        "another-secret-key-of-at-least-32-characters",
        issued_at=datetime.now(UTC),
        ttl=timedelta(hours=1),
    )

    response = send(anonymous_client, method, path, body, {"Authorization": f"Bearer {token}"})

    assert_unauthorized(response, INVALID_TOKEN)


@pytest.mark.parametrize(("method", "path", "body"), PROTECTED)
def test_a_protected_route_rejects_a_changed_token(
    client: TestClient, method: str, path: str, body: object
) -> None:
    changed = f"{client.headers['Authorization']}x"

    response = send(client, method, path, body, {"Authorization": changed})

    assert_unauthorized(response, INVALID_TOKEN)


@pytest.mark.parametrize(("method", "path", "body"), PROTECTED)
def test_a_protected_route_rejects_an_expired_token(
    anonymous_client: TestClient, settings: Settings, method: str, path: str, body: object
) -> None:
    ttl = timedelta(seconds=settings.auth_token_ttl_seconds)
    token = token_signed_with(
        settings.auth_secret_key.get_secret_value(),
        issued_at=datetime.now(UTC) - ttl - timedelta(seconds=1),
        ttl=ttl,
    )

    response = send(anonymous_client, method, path, body, {"Authorization": f"Bearer {token}"})

    assert_unauthorized(response, INVALID_TOKEN)


def test_a_valid_token_keeps_the_behavior_of_every_protected_route(client: TestClient) -> None:
    id = MotherCreator.uuid()

    assert client.put(f"/feed/{id}", json=FEED).status_code == 201
    assert client.patch(f"/feed/{id}", json={"title": "Another title"}).status_code == 200
    assert client.delete(f"/feed/{id}").status_code == 204
    assert client.get("/feed/scrap").status_code == 200


def test_the_bearer_scheme_is_case_insensitive(client: TestClient) -> None:
    token = client.headers["Authorization"].removeprefix("Bearer ")

    response = client.put(
        f"/feed/{MotherCreator.uuid()}", json=FEED, headers={"Authorization": f"bearer {token}"}
    )

    assert response.status_code == 201


@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        pytest.param(b'{"title": 1}', "application/json", id="invalid field"),
        pytest.param(b"{not json", "application/json", id="malformed json"),
        pytest.param(b"title=A title", "text/plain", id="another content type"),
        pytest.param(b"", "application/json", id="empty body"),
    ],
)
def test_authentication_wins_over_an_invalid_body(
    anonymous_client: TestClient, content: bytes, content_type: str
) -> None:
    response = anonymous_client.put(
        f"/feed/{MotherCreator.uuid()}", content=content, headers={"content-type": content_type}
    )

    assert_unauthorized(response, AUTHENTICATION_REQUIRED)


def test_authentication_wins_over_a_missing_feed(anonymous_client: TestClient) -> None:
    response = anonymous_client.delete(f"/feed/{MotherCreator.uuid()}")

    assert_unauthorized(response, AUTHENTICATION_REQUIRED)


def test_authentication_wins_over_an_invalid_id(anonymous_client: TestClient) -> None:
    response = anonymous_client.patch("/feed/not-a-uuid", json={"title": "Another title"})

    assert_unauthorized(response, AUTHENTICATION_REQUIRED)


def test_an_unauthenticated_scrape_reads_no_front_page(
    anonymous_client: TestClient, front_pages_transport: FrontPagesTransport
) -> None:
    response = anonymous_client.get("/feed/scrap")

    assert_unauthorized(response, AUTHENTICATION_REQUIRED)
    assert front_pages_transport.requests == []


@pytest.mark.parametrize(
    ("path", "status_code"),
    [
        ("/feed/list", 200),
        ("/feed/home", 200),
        ("/feed/{id}", 404),
        ("/status", 200),
        ("/docs", 200),
        ("/redoc", 200),
        ("/openapi.json", 200),
    ],
)
def test_public_routes_answer_without_a_token(
    anonymous_client: TestClient, path: str, status_code: int
) -> None:
    response = anonymous_client.get(path.format(id=MotherCreator.uuid()))

    assert response.status_code == status_code
