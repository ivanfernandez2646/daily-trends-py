import os
import socket
import subprocess
import sys

RUN_MAIN = "from daily_trends_py.apps.cms_backend.main import main; main()"


def run_main(**environment: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", RUN_MAIN],
        env={**os.environ, **environment},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_exits_with_code_1_when_configuration_is_invalid() -> None:
    result = run_main(ENV="staging")

    assert result.returncode == 1
    assert "Startup failed" in result.stderr


def test_exits_with_code_1_when_port_is_already_in_use() -> None:
    with socket.socket() as busy_socket:
        busy_socket.bind(("0.0.0.0", 0))
        busy_socket.listen()
        busy_port = busy_socket.getsockname()[1]

        result = run_main(PORT=str(busy_port))

    assert result.returncode == 1
