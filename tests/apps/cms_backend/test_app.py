import pytest
from fastapi import Response
from fastapi.testclient import TestClient

from daily_trends_py.apps.cms_backend.container import create_container
from daily_trends_py.apps.cms_backend.main import create_app
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.migration import (  # noqa: E501
    Migration,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
)
from tests.apps.cms_backend.conftest import resolve_mongo_client, run_in_app
from tests.apps.cms_backend.isolated_settings import IsolatedSettings
from tests.mongo import TEST_MONGO_URL, fresh_database_name, mongo_url_for

pytestmark = pytest.mark.integration


def test_unhandled_error_returns_500_as_json_and_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(create_container(IsolatedSettings(mongo_url=TEST_MONGO_URL)))

    @app.get("/unhandled")
    async def unhandled() -> Response:  # pyright: ignore[reportUnusedFunction]
        raise RuntimeError("boom")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/unhandled")

    assert response.status_code == 500
    assert response.json() == {"error": "boom"}
    assert response.headers["content-type"] == "application/json"
    assert any(record.exc_info and record.exc_info[1] is not None for record in caplog.records)


def test_applies_migrations_before_taking_traffic() -> None:
    database = fresh_database_name("daily-trends-test-startup")
    applied: list[str] = []

    async def up(db: MongoDatabase) -> None:
        applied.append(db.name)

    container = create_container(
        IsolatedSettings(mongo_url=mongo_url_for(database)),
        migrations=[Migration("m_test_records", up)],
    )

    with TestClient(create_app(container)) as client:
        mongo_client = resolve_mongo_client(client, container)
        try:
            assert applied == [database]
            migration = run_in_app(
                client, lambda: mongo_client[database]["migrations"].find_one("m_test_records")
            )
            assert migration is not None and migration["status"] == "applied"
            assert client.get("/status").is_success
        finally:
            run_in_app(client, lambda: mongo_client.drop_database(database))


def test_allows_any_origin(client: TestClient) -> None:
    response = client.get("/status", headers={"Origin": "https://example.com"})

    assert response.headers["access-control-allow-origin"] == "*"


def test_accepts_preflight_requesting_any_header(client: TestClient) -> None:
    response = client.options(
        "/status",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "x-custom-header",
        },
    )

    assert response.is_success
    assert response.headers["access-control-allow-origin"] == "*"
    assert "x-custom-header" in response.headers["access-control-allow-headers"].lower()


def test_compresses_large_responses(client: TestClient) -> None:
    response = client.get("/openapi.json", headers={"Accept-Encoding": "gzip"})

    assert response.headers["content-encoding"] == "gzip"


def test_does_not_compress_small_responses(client: TestClient) -> None:
    response = client.get("/status", headers={"Accept-Encoding": "gzip"})

    assert "content-encoding" not in response.headers


@pytest.mark.parametrize("path", ["/docs", "/redoc"])
def test_serves_the_generated_docs(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "/openapi.json" in response.text


def test_serves_the_generated_openapi_document(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["openapi"].startswith("3.")


@pytest.mark.parametrize("path", ["/", "/openapi.yml"])
def test_no_longer_serves_the_hand_written_document(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 404
