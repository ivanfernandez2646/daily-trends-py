import io
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Callable, Iterator
from pathlib import Path

import pytest

from daily_trends_py.apps.cms_backend.cli import create_admin
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.mongo_client_factory import (  # noqa: E501
    MongoDatabase,
    create_mongo_client,
)
from tests.apps.cms_backend.isolated_settings import IsolatedSettings
from tests.mongo import fresh_database_name, mongo_url_for

pytestmark = pytest.mark.integration

PASSWORD = "a-long-enough-secret"


@pytest.fixture
def database_name() -> str:
    return fresh_database_name("daily-trends-test-cli")


@pytest.fixture
def settings(database_name: str) -> IsolatedSettings:
    return IsolatedSettings(mongo_url=mongo_url_for(database_name))


@pytest.fixture
async def db(settings: IsolatedSettings, database_name: str) -> AsyncIterator[MongoDatabase]:
    client = await create_mongo_client(settings.mongo_url)
    yield client.get_default_database()
    await client.drop_database(database_name)
    await client.close()


def answers(*values: str) -> Callable[[str], str]:
    """A prompt that answers `values` in order and records nothing else."""
    remaining: Iterator[str] = iter(values)
    return lambda _question: next(remaining)


def no_prompt(question: str) -> str:
    raise AssertionError(f"Unexpected prompt: {question}")


def run_entry_point(
    *arguments: str, settings: IsolatedSettings, cwd: Path, stdin: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from daily_trends_py.apps.cms_backend.main import main; main()",
            *arguments,
        ],
        cwd=cwd,
        env={**os.environ, "MONGO_URL": settings.mongo_url},
        input=stdin,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


async def emails(db: MongoDatabase) -> list[str]:
    return [str(doc["email"]) async for doc in db["users"].find()]


async def test_creates_an_admin_on_an_empty_database_with_the_given_email(
    settings: IsolatedSettings, db: MongoDatabase, capsys: pytest.CaptureFixture[str]
) -> None:
    code = await create_admin(
        settings,
        email="Admin@Example.com",
        prompt=no_prompt,
        secret_prompt=answers(PASSWORD, PASSWORD),
    )

    output = capsys.readouterr()
    assert code == 0
    assert output.out == "Admin <admin@example.com> created\n"
    assert await emails(db) == ["admin@example.com"]
    assert "email_unique" in await db["users"].index_information()
    assert PASSWORD not in output.out + output.err


async def test_asks_for_the_email_when_it_is_not_given(
    settings: IsolatedSettings, db: MongoDatabase
) -> None:
    code = await create_admin(
        settings,
        email=None,
        prompt=answers("admin@example.com"),
        secret_prompt=answers(PASSWORD, PASSWORD),
    )

    assert code == 0
    assert await emails(db) == ["admin@example.com"]


@pytest.mark.parametrize(
    ("email", "passwords", "message"),
    [
        pytest.param(
            "admin@example.com",
            (PASSWORD, f"{PASSWORD}!"),
            "Passwords do not match",
            id="passwords differ",
        ),
        pytest.param(
            "admin@example.com",
            ("shortsecret", "shortsecret"),
            "<UserPassword> must have at least 12 characters",
            id="short password",
        ),
        pytest.param(
            "not-an-email",
            (PASSWORD, PASSWORD),
            "<UserEmail> does not allow the value <not-an-email>",
            id="invalid email",
        ),
    ],
)
async def test_fails_with_code_1_without_creating_anything(
    settings: IsolatedSettings,
    db: MongoDatabase,
    capsys: pytest.CaptureFixture[str],
    email: str,
    passwords: tuple[str, str],
    message: str,
) -> None:
    code = await create_admin(
        settings, email=email, prompt=no_prompt, secret_prompt=answers(*passwords)
    )

    output = capsys.readouterr()
    assert code == 1
    assert output.err == f"{message}\n"
    assert output.out == ""
    assert await emails(db) == []
    assert all(password not in output.err for password in passwords)


async def test_a_second_admin_with_the_same_email_fails_with_code_1(
    settings: IsolatedSettings, db: MongoDatabase, capsys: pytest.CaptureFixture[str]
) -> None:
    await create_admin(
        settings,
        email="admin@example.com",
        prompt=no_prompt,
        secret_prompt=answers(PASSWORD, PASSWORD),
    )
    capsys.readouterr()

    code = await create_admin(
        settings,
        email="ADMIN@example.com",
        prompt=no_prompt,
        secret_prompt=answers("another-long-secret", "another-long-secret"),
    )

    assert code == 1
    assert capsys.readouterr().err == "User with email <admin@example.com> already exists\n"
    assert await emails(db) == ["admin@example.com"]


async def test_the_create_admin_subcommand_of_the_entry_point_creates_an_admin(
    settings: IsolatedSettings, db: MongoDatabase, tmp_path: Path
) -> None:
    # Without a terminal, the password prompt reads standard input.
    result = run_entry_point(
        "create-admin",
        "--email",
        "admin@example.com",
        settings=settings,
        cwd=tmp_path,
        stdin=f"{PASSWORD}\n{PASSWORD}\n",
    )

    assert result.returncode == 0, result.stderr
    assert "Admin <admin@example.com> created" in result.stdout
    assert PASSWORD not in result.stdout + result.stderr
    assert await emails(db) == ["admin@example.com"]


@pytest.mark.parametrize(
    "line",
    [
        pytest.param(f"{PASSWORD}\n", id="newline"),
        pytest.param(f"{PASSWORD}\r\n", id="carriage return and newline"),
        pytest.param(PASSWORD, id="no final newline"),
        pytest.param(f"{PASSWORD}\nignored second line\n", id="more lines"),
    ],
)
async def test_reads_the_password_once_from_the_first_line_of_the_given_input(
    settings: IsolatedSettings, db: MongoDatabase, capsys: pytest.CaptureFixture[str], line: str
) -> None:
    code = await create_admin(
        settings,
        email="admin@example.com",
        prompt=no_prompt,
        secret_prompt=no_prompt,
        password_from=io.StringIO(line),
    )

    output = capsys.readouterr()
    assert code == 0, output.err
    assert output.out == "Admin <admin@example.com> created\n"
    assert await emails(db) == ["admin@example.com"]
    assert PASSWORD not in output.out + output.err


@pytest.mark.parametrize(
    ("email", "line", "message"),
    [
        pytest.param(
            "admin@example.com",
            "shortsecret\n",
            "<UserPassword> must have at least 12 characters",
            id="short password",
        ),
        pytest.param(
            "admin@example.com",
            "",
            "<UserPassword> must have at least 12 characters",
            id="empty input",
        ),
        pytest.param(
            "not-an-email",
            f"{PASSWORD}\n",
            "<UserEmail> does not allow the value <not-an-email>",
            id="invalid email",
        ),
    ],
)
async def test_a_password_from_the_input_is_validated_like_a_typed_one(
    settings: IsolatedSettings,
    db: MongoDatabase,
    capsys: pytest.CaptureFixture[str],
    email: str,
    line: str,
    message: str,
) -> None:
    code = await create_admin(
        settings,
        email=email,
        prompt=no_prompt,
        secret_prompt=no_prompt,
        password_from=io.StringIO(line),
    )

    output = capsys.readouterr()
    assert code == 1
    assert output.err == f"{message}\n"
    assert output.out == ""
    assert await emails(db) == []
    assert line.strip() == "" or line.strip() not in output.err


async def test_a_duplicate_admin_from_the_input_fails_with_code_1(
    settings: IsolatedSettings, db: MongoDatabase, capsys: pytest.CaptureFixture[str]
) -> None:
    await create_admin(
        settings,
        email="admin@example.com",
        prompt=no_prompt,
        secret_prompt=no_prompt,
        password_from=io.StringIO(f"{PASSWORD}\n"),
    )
    capsys.readouterr()

    code = await create_admin(
        settings,
        email="admin@example.com",
        prompt=no_prompt,
        secret_prompt=no_prompt,
        password_from=io.StringIO(f"{PASSWORD}\n"),
    )

    assert code == 1
    assert capsys.readouterr().err == "User with email <admin@example.com> already exists\n"


async def test_the_entry_point_reads_one_password_line_with_password_stdin(
    settings: IsolatedSettings, db: MongoDatabase, tmp_path: Path
) -> None:
    result = run_entry_point(
        "create-admin",
        "--email",
        "admin@example.com",
        "--password-stdin",
        settings=settings,
        cwd=tmp_path,
        stdin=f"{PASSWORD}\n",
    )

    assert result.returncode == 0, result.stderr
    assert "Admin <admin@example.com> created" in result.stdout
    assert PASSWORD not in result.stdout + result.stderr
    assert await emails(db) == ["admin@example.com"]


async def test_password_stdin_without_an_email_is_a_usage_error(
    settings: IsolatedSettings, db: MongoDatabase, tmp_path: Path
) -> None:
    result = run_entry_point(
        "create-admin", "--password-stdin", settings=settings, cwd=tmp_path, stdin=f"{PASSWORD}\n"
    )

    assert result.returncode == 2
    assert "--password-stdin requires --email" in result.stderr
    assert await emails(db) == []
