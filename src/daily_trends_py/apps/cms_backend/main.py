import argparse
import asyncio
import getpass
import json
import logging
import sys
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from importlib.metadata import version

import uvicorn
from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from uvicorn.config import STARTUP_FAILURE

from daily_trends_py.apps.cms_backend.api import CmsBackendApi
from daily_trends_py.apps.cms_backend.cli import create_admin
from daily_trends_py.apps.cms_backend.container import STARTUP_DEPENDENCIES, create_container
from daily_trends_py.apps.cms_backend.errors import register_error_handling
from daily_trends_py.apps.cms_backend.routes import register_routes
from daily_trends_py.apps.cms_backend.settings import Settings
from daily_trends_py.contexts.cms.feeds.application.scrape.feed_scrape_scheduler import (
    FeedScrapeScheduler,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.migration import (  # noqa: E501
    Migration,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    MIGRATIONS,
)

logger = logging.getLogger(__name__)

DESCRIPTION = (
    "Front-page news feeds: CMS feeds managed through this API and headlines scraped from"
    " El Mundo, El Español, El Confidencial, La Razón and La Vanguardia. The front pages are"
    " scraped when the API starts and then every 2 hours by default (`SCRAPE_INTERVAL_SECONDS`),"
    " and `/feed/scrap` scrapes them on demand."
    " Creating, updating and deleting feeds and `/feed/scrap` need an administrator's bearer"
    " access token, from `/auth/login`, and so does `/auth/me`, which answers who the token"
    " belongs to and when it expires; reading feeds is public."
    ' Every error answers `{"error": "<message>"}`: 400 for an invalid request, 401 for missing'
    " or invalid credentials, 404 for a missing feed, 409 for an existing id, and 500 for"
    ' anything else, always with `{"error": "Internal server error"}`.'
)


def create_app(container: AsyncContainer) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        try:
            # An unreachable Mongo or a failing migration stops startup before the app takes
            # traffic.
            for dependency in STARTUP_DEPENDENCIES:
                await container.get(dependency)
            settings = await container.get(Settings)
            if settings.scrape_schedule_enabled:
                (await container.get(FeedScrapeScheduler)).start()
            yield
        finally:
            await container.close()

    app = CmsBackendApi(
        title="Daily trends",
        version=version("daily-trends-py"),
        description=DESCRIPTION,
        lifespan=lifespan,
    )
    # The last middleware added runs first: errors are answered inside compression and CORS.
    register_error_handling(app)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "HEAD", "PUT", "PATCH", "POST", "DELETE"],
        allow_headers=["*"],
    )
    register_routes(app)
    setup_dishka(container, app)
    return app


CREATE_ADMIN = "create-admin"
OPENAPI = "openapi"


def main(
    argv: Sequence[str] | None = None, *, migrations: Sequence[Migration] = MIGRATIONS
) -> None:
    """Run the API, or the subcommand given in `argv` (the command line by default)."""
    parser = _parser()
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    if arguments.command == CREATE_ADMIN:
        # The email prompt would read standard input too, before the password.
        if arguments.password_stdin and arguments.email is None:
            parser.error("--password-stdin requires --email")
        sys.exit(_create_admin(arguments.email, arguments.password_stdin, migrations))
    if arguments.command == OPENAPI:
        print(json.dumps(openapi_document(), indent=2, ensure_ascii=False))
        return
    _serve(migrations)


def openapi_document() -> dict[str, object]:
    """The OpenAPI document of the API, built without starting it or connecting to Mongo."""
    # The document depends on no setting, so the environment and `.env` are not read: an
    # incomplete production configuration still prints it.
    return create_app(create_container(Settings.model_construct())).openapi()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="daily-trends-py", description="Run the API.")
    commands = parser.add_subparsers(dest="command")
    create = commands.add_parser(
        CREATE_ADMIN,
        help=(
            "Create an administrator; the password is asked twice, without echo, unless"
            " --password-stdin is given."
        ),
    )
    create.add_argument("--email", help="Asked for when it is not given.")
    create.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read the password from the first line of standard input.",
    )
    commands.add_parser(OPENAPI, help="Print the OpenAPI document of the API, without starting it.")
    return parser


def _create_admin(email: str | None, password_stdin: bool, migrations: Sequence[Migration]) -> int:
    try:
        return asyncio.run(
            create_admin(
                Settings(),
                email=email,
                prompt=input,
                secret_prompt=getpass.getpass,
                migrations=migrations,
                password_from=sys.stdin if password_stdin else None,
            )
        )
    except Exception:
        logger.exception("Creating the admin failed")
        return 1


def _serve(migrations: Sequence[Migration]) -> None:
    try:
        settings = Settings()
        container = create_container(settings, migrations=migrations)
        uvicorn.run(create_app(container), host="0.0.0.0", port=settings.port)
    except SystemExit as error:
        # uvicorn logs why it could not start and exits with its own code (3).
        if error.code == STARTUP_FAILURE:
            sys.exit(1)
        raise
    except Exception:
        logger.exception("Startup failed")
        sys.exit(1)
