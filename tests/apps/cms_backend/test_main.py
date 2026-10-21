import json
import os
import socket
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest
from pymongo import MongoClient

from daily_trends_py.apps.cms_backend.container import create_container
from daily_trends_py.apps.cms_backend.main import create_app, main
from tests.apps.cms_backend.isolated_settings import IsolatedSettings
from tests.mongo import TEST_MONGO_URL, fresh_database_name, mongo_url_for

RUN_MAIN = "from daily_trends_py.apps.cms_backend.main import main; main()"

RUN_OPENAPI = "from daily_trends_py.apps.cms_backend.main import main; main(['openapi'])"

RUN_MAIN_WITH_FAILING_MIGRATION = """
from daily_trends_py.apps.cms_backend.main import main
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations import (
    migration,
)

async def up(db):
    raise RuntimeError("boom")

main([], migrations=[migration.Migration("m_test_fails", up)])
"""


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("0.0.0.0", 0))
        return probe.getsockname()[1]


def run_main(
    cwd: Path,
    base_environment: Mapping[str, str] = os.environ,
    script: str = RUN_MAIN,
    **environment: str,
) -> subprocess.CompletedProcess[str]:
    # Runs outside the repository so a local `.env` is never read.
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=cwd,
        env={**base_environment, "PORT": str(free_port()), **environment},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_exits_with_code_1_when_configuration_is_invalid(tmp_path: Path) -> None:
    result = run_main(tmp_path, ENV="staging")

    assert result.returncode == 1
    assert "Startup failed" in result.stderr


def test_exits_with_code_1_when_the_timezone_is_unknown(tmp_path: Path) -> None:
    result = run_main(tmp_path, TIMEZONE="Mars/Olympus")

    assert result.returncode == 1
    assert "Startup failed" in result.stderr


def test_exits_with_code_1_without_mongo_url_in_production(tmp_path: Path) -> None:
    without_mongo_url = {name: value for name, value in os.environ.items() if name != "MONGO_URL"}

    result = run_main(tmp_path, without_mongo_url, ENV="production")

    assert result.returncode == 1
    assert "Startup failed" in result.stderr
    assert "MONGO_URL" in result.stderr


def test_exits_with_code_1_without_a_secret_key_in_production(tmp_path: Path) -> None:
    without_secret_key = {
        name: value for name, value in os.environ.items() if name != "AUTH_SECRET_KEY"
    }

    result = run_main(
        tmp_path, without_secret_key, ENV="production", MONGO_URL="mongodb://mongo:27017/x"
    )

    assert result.returncode == 1
    assert "Startup failed" in result.stderr
    assert "AUTH_SECRET_KEY" in result.stderr


def test_exits_with_code_1_when_mongo_is_unreachable(tmp_path: Path) -> None:
    result = run_main(
        tmp_path, MONGO_URL="mongodb://localhost:1/daily-trends?serverSelectionTimeoutMS=100"
    )

    assert result.returncode == 1


@pytest.mark.integration
def test_exits_with_code_1_when_port_is_already_in_use(tmp_path: Path) -> None:
    with socket.socket() as busy_socket:
        busy_socket.bind(("0.0.0.0", 0))
        busy_socket.listen()
        busy_port = busy_socket.getsockname()[1]

        result = run_main(tmp_path, PORT=str(busy_port))

    assert result.returncode == 1


@pytest.mark.integration
def test_exits_with_code_1_when_a_migration_fails(tmp_path: Path) -> None:
    database = fresh_database_name("daily-trends-test-startup")
    try:
        result = run_main(
            tmp_path,
            script=RUN_MAIN_WITH_FAILING_MIGRATION,
            MONGO_URL=mongo_url_for(database),
        )
    finally:
        with MongoClient[dict[str, object]](TEST_MONGO_URL) as client:
            client.drop_database(database)

    assert result.returncode == 1
    assert "Migration m_test_fails failed" in result.stderr


def test_openapi_prints_the_document_of_the_app(capsys: pytest.CaptureFixture[str]) -> None:
    main(["openapi"])

    printed = json.loads(capsys.readouterr().out)
    app = create_app(create_container(IsolatedSettings(mongo_url=TEST_MONGO_URL)))
    assert printed == app.openapi()


def test_openapi_needs_neither_configuration_nor_mongo(tmp_path: Path) -> None:
    without_required_settings = {
        name: value
        for name, value in os.environ.items()
        if name not in {"MONGO_URL", "AUTH_SECRET_KEY"}
    }
    (tmp_path / ".env").write_text("TIMEZONE=Mars/Olympus\n")

    result = run_main(tmp_path, without_required_settings, script=RUN_OPENAPI, ENV="production")

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["info"]["title"] == "Daily trends"
