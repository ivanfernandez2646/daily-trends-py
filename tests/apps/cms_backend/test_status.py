import pytest
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

pytestmark = pytest.mark.integration

scenarios("features/status.feature")


def test_status_answers_with_empty_body(client: TestClient) -> None:
    response = client.get("/status")

    assert response.content == b""
