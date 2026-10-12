from collections.abc import Iterator

import pytest
from dishka import Provider, make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import APIRouter, FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

from daily_trends_py.apps.cms_backend.errors import register_error_handling
from daily_trends_py.apps.cms_backend.http.json_body_route import JsonBodyRoute

WRONG_CONTENT_TYPE = {"error": "body: Content type should be application/json"}


class Body(BaseModel):
    title: str


@pytest.fixture
def client() -> Iterator[TestClient]:
    router = APIRouter(route_class=JsonBodyRoute)

    @router.put("/with-body")
    async def with_body(body: Body) -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        return {"title": body.title}

    @router.get("/without-body")
    async def without_body(request: Request) -> dict[str, str | None]:  # pyright: ignore[reportUnusedFunction]
        return {"content-type": request.headers.get("content-type")}

    app = FastAPI()
    register_error_handling(app)
    app.include_router(router)
    setup_dishka(make_async_container(Provider()), app)
    with TestClient(app) as test_client:
        yield test_client


def test_accepts_a_json_body(client: TestClient) -> None:
    response = client.put("/with-body", json={"title": "A title"})

    assert response.json() == {"title": "A title"}


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="no body"),
        pytest.param({"content-type": "application/json"}, id="empty JSON body"),
    ],
)
def test_reads_a_missing_or_empty_body_as_an_empty_object(
    client: TestClient, headers: dict[str, str]
) -> None:
    response = client.put("/with-body", headers=headers)

    assert response.status_code == 400
    assert response.json() == {"error": "title: Field required"}


@pytest.mark.parametrize(
    "content_type",
    [
        pytest.param("application/x-www-form-urlencoded", id="urlencoded"),
        pytest.param("application/merge-patch+json", id="another JSON type"),
        pytest.param("text/plain", id="plain text"),
        pytest.param(None, id="none"),
    ],
)
def test_rejects_a_body_that_is_not_application_json(
    client: TestClient, content_type: str | None
) -> None:
    headers = {} if content_type is None else {"content-type": content_type}

    response = client.put("/with-body", content='{"title": "A title"}', headers=headers)

    assert response.status_code == 400
    assert response.json() == WRONG_CONTENT_TYPE


def test_accepts_json_with_a_charset(client: TestClient) -> None:
    response = client.put(
        "/with-body",
        content='{"title": "A title"}',
        headers={"content-type": "application/json; charset=utf-8"},
    )

    assert response.json() == {"title": "A title"}


def test_leaves_routes_without_a_body_untouched(client: TestClient) -> None:
    response = client.get("/without-body")

    assert response.json() == {"content-type": None}
