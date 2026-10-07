import httpx2
from fastapi.testclient import TestClient
from pytest_bdd import parsers, scenarios, then, when

scenarios("features/status.feature")


@when(parsers.parse('I send a GET request to "{path}"'), target_fixture="response")
def send_get_request(client: TestClient, path: str) -> httpx2.Response:
    return client.get(path)


@then(parsers.parse("The response status code should be {status_code:d}"))
def response_status_code_is(response: httpx2.Response, status_code: int) -> None:
    assert response.status_code == status_code


def test_status_answers_with_empty_body(client: TestClient) -> None:
    response = client.get("/status")

    assert response.content == b""
