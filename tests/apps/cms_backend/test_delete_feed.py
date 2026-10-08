import pytest
from fastapi.testclient import TestClient
from pytest_bdd import scenarios

from tests.contexts.cms.shared.domain.mother_creator import MotherCreator

pytestmark = pytest.mark.integration

scenarios("features/delete-feed.feature")


def test_a_deleted_feed_is_no_longer_found(client: TestClient) -> None:
    id = MotherCreator.uuid()
    client.put(f"/feed/{id}", json={"title": "A title", "author": "Ivan"})

    assert client.delete(f"/feed/{id}").status_code == 200

    response = client.get(f"/feed/{id}")
    assert response.status_code == 404
    assert response.json() == {"error": f"Feed with id <{id}> not found"}


def test_rejects_an_id_that_is_not_a_uuid(client: TestClient) -> None:
    response = client.delete("/feed/not-a-uuid")

    assert response.status_code == 400
    assert response.json() == {"error": "<FeedId> does not allow the value <not-a-uuid>"}
