from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from daily_trends_py.apps.cms_backend.main import create_app
from daily_trends_py.apps.cms_backend.settings import Settings


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app(Settings())) as test_client:
        yield test_client
