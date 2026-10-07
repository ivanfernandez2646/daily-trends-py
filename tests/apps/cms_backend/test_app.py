import pytest
from fastapi import Response
from fastapi.testclient import TestClient

from daily_trends_py.apps.cms_backend.main import create_app
from daily_trends_py.apps.cms_backend.settings import Settings

pytestmark = pytest.mark.integration


def test_unhandled_error_returns_500_with_plain_message_and_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(Settings())

    @app.get("/unhandled")
    async def unhandled() -> Response:  # pyright: ignore[reportUnusedFunction]
        raise RuntimeError("boom")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/unhandled")

    assert response.status_code == 500
    assert response.text == "boom"
    assert response.headers["content-type"].startswith("text/plain")
    assert any(record.exc_info and record.exc_info[1] is not None for record in caplog.records)


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
    response = client.get("/openapi.yml", headers={"Accept-Encoding": "gzip"})

    assert response.headers["content-encoding"] == "gzip"


def test_does_not_compress_small_responses(client: TestClient) -> None:
    response = client.get("/status", headers={"Accept-Encoding": "gzip"})

    assert "content-encoding" not in response.headers


def test_serves_swagger_ui_at_root_loading_the_openapi_document(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "/openapi.yml" in response.text


def test_serves_the_openapi_document(client: TestClient) -> None:
    response = client.get("/openapi.yml")

    assert response.status_code == 200
    assert response.text.startswith("openapi:")


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_does_not_expose_fastapi_generated_docs(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 404
