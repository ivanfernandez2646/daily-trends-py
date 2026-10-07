import pytest
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

pytestmark = pytest.mark.integration

scenarios("features/find-feed.feature")


def test_rejects_an_id_that_is_not_a_uuid(client: TestClient) -> None:
    response = client.get("/feed/not-a-uuid")

    assert response.status_code == 400
    assert response.json() == {"error": "<FeedId> does not allow the value <not-a-uuid>"}
