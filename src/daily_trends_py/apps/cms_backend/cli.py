import sys
from collections.abc import Callable, Sequence
from typing import TextIO

from daily_trends_py.apps.cms_backend.container import create_container
from daily_trends_py.apps.cms_backend.settings import Settings
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.migration import (  # noqa: E501
    Migration,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    MIGRATIONS,
)
from daily_trends_py.contexts.cms.users.application.create.user_creator import UserCreator
from daily_trends_py.contexts.cms.users.domain.errors import UserAlreadyExists

type Prompt = Callable[[str], str]


async def create_admin(
    settings: Settings,
    *,
    email: str | None,
    prompt: Prompt,
    secret_prompt: Prompt,
    migrations: Sequence[Migration] = MIGRATIONS,
    password_from: TextIO | None = None,
) -> int:
    """Create an administrator and answer the exit code; the password is never printed.

    With `password_from`, the password is its first line, read once, for scripts.
    """
    email = email if email is not None else prompt("Email: ")
    if password_from is not None:
        password = password_from.readline().rstrip("\r\n")
    else:
        password = secret_prompt("Password: ")
        if secret_prompt("Repeat password: ") != password:
            print("Passwords do not match", file=sys.stderr)
            return 1

    # Resolving the use case connects to Mongo and applies pending migrations first.
    container = create_container(settings, migrations=migrations)
    try:
        creator = await container.get(UserCreator)
        user = await creator.execute(email=email, password=password)
    except (InvalidArgumentError, UserAlreadyExists) as error:
        print(error, file=sys.stderr)
        return 1
    finally:
        await container.close()
    print(f"Admin <{user.email.value}> created")
    return 0
