import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from tests.mongo import TEST_MONGO_URL, mongo_unreachable_message, redacted_mongo_url

ROOT = Path(__file__).parent.parent
CLOSED_PORT_URL = "mongodb://localhost:1/daily-trends-test"
# One unit test and one integration test.
MIXED_MODULE = (
    "tests/contexts/cms/shared/infrastructure/persistence/mongo/migrations/versions/"
    "test_migrations_list.py"
)


@pytest.mark.parametrize(
    ("url", "redacted"),
    [
        pytest.param(
            "mongodb://user:secret@host:27017/db?authSource=admin&serverSelectionTimeoutMS=2000",
            "mongodb://host:27017/db",
            id="with credentials and options",
        ),
        pytest.param("mongodb://localhost:27017/db", "mongodb://localhost:27017/db", id="plain"),
    ],
)
def test_redacted_mongo_url_keeps_only_scheme_host_port_and_database(
    url: str, redacted: str
) -> None:
    assert redacted_mongo_url(url) == redacted


async def test_mongo_unreachable_message_names_the_redacted_url_quickly() -> None:
    started = time.monotonic()

    message = await mongo_unreachable_message(
        "mongodb://user:secret@localhost:1/db?serverSelectionTimeoutMS=200"
    )

    assert message == (
        "MongoDB is not reachable at mongodb://localhost:1/db; "
        "start it with: docker compose up -d --wait mongo"
    )
    assert time.monotonic() - started < 5


@pytest.mark.integration
async def test_mongo_unreachable_message_is_none_when_mongo_answers() -> None:
    assert await mongo_unreachable_message(TEST_MONGO_URL) is None


def test_the_test_mongo_url_has_a_short_server_selection_timeout() -> None:
    options = parse_qs(urlsplit(TEST_MONGO_URL).query)

    assert options["serverSelectionTimeoutMS"] == ["2000"]


def test_the_test_mongo_url_keeps_the_options_of_mongo_url() -> None:
    url = run_python(
        "from tests.mongo import TEST_MONGO_URL; print(TEST_MONGO_URL)",
        "mongodb://localhost:27017/daily-trends-test?authSource=admin",
    ).stdout.strip()

    assert parse_qs(urlsplit(url).query) == {
        "authSource": ["admin"],
        "serverSelectionTimeoutMS": ["2000"],
    }


def test_a_session_with_integration_tests_fails_at_once_without_mongo() -> None:
    started = time.monotonic()

    result = run_pytest(MIXED_MODULE)

    assert result.returncode == 1
    assert (
        "MongoDB is not reachable at mongodb://localhost:1/daily-trends-test; "
        "start it with: docker compose up -d --wait mongo"
    ) in result.stdout + result.stderr
    assert time.monotonic() - started < 15


def test_a_session_without_integration_tests_passes_without_mongo() -> None:
    result = run_pytest(MIXED_MODULE, "-m", "not integration")

    assert result.returncode == 0, result.stdout
    assert "1 passed, 1 deselected" in result.stdout


def run_pytest(*args: str) -> subprocess.CompletedProcess[str]:
    return run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", *args], CLOSED_PORT_URL
    )


def run_python(code: str, mongo_url: str) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, "-c", code], mongo_url)


def run(command: list[str], mongo_url: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, "MONGO_URL": mongo_url},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
