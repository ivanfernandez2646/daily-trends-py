import logging
import sys
from types import TracebackType

import uvicorn
from fastapi import FastAPI
from uvicorn.config import STARTUP_FAILURE

from daily_trends_py.apps.cms_backend.routes import status
from daily_trends_py.apps.cms_backend.settings import Settings

logger = logging.getLogger(__name__)


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.include_router(status.router)
    return app


def _log_uncaught_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    traceback: TracebackType | None,
) -> None:
    # The interpreter exits with code 1 after the hook returns.
    logger.critical("uncaughtException", exc_info=(exc_type, exc_value, traceback))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    sys.excepthook = _log_uncaught_exception
    try:
        settings = Settings()
        uvicorn.run(create_app(settings), host="0.0.0.0", port=settings.port)
    except SystemExit as error:
        # uvicorn logs why it could not start and exits with its own code (3).
        if error.code == STARTUP_FAILURE:
            sys.exit(1)
        raise
    except Exception:
        logger.exception("Startup failed")
        sys.exit(1)
