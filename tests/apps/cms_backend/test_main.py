import os
import socket
import subprocess
import sys

import pytest

RUN_MAIN = "from daily_trends_py.apps.cms_backend.main import main; main()"


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("0.0.0.0", 0))
        return probe.getsockname()[1]


def run_main(**environment: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", RUN_MAIN],
        env={**os.environ, "PORT": str(free_port()), **environment},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_exits_with_code_1_when_configuration_is_invalid() -> None:
    result = run_main(ENV="staging")

    assert result.returncode == 1
    assert "Startup failed" in result.stderr


def test_exits_with_code_1_when_mongo_is_unreachable() -> None:
    result = run_main(MONGO_URL="mongodb://localhost:1/daily-trends?serverSelectionTimeoutMS=100")

    assert result.returncode == 1


@pytest.mark.integration
def test_exits_with_code_1_when_port_is_already_in_use() -> None:
    with socket.socket() as busy_socket:
        busy_socket.bind(("0.0.0.0", 0))
        busy_socket.listen()
        busy_port = busy_socket.getsockname()[1]

        result = run_main(PORT=str(busy_port))

    assert result.returncode == 1
