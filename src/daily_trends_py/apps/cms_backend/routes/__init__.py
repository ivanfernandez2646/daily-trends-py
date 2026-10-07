from fastapi import FastAPI

from daily_trends_py.apps.cms_backend.routes import status, swagger


def register_routes(app: FastAPI) -> None:
    """Register every router.

    Fixed routes (`/feed/list`, `/feed/home`, `/feed/scrap`) must be registered before
    `/feed/{id}`, so a fixed path is never read as an id.
    """
    app.include_router(status.router)
    app.include_router(swagger.router)
