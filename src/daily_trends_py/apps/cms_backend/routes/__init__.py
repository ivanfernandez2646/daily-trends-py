from fastapi import FastAPI

from daily_trends_py.apps.cms_backend.routes import auth, feed, status


def register_routes(app: FastAPI) -> None:
    """Register every router.

    Fixed routes (`/feed/list`, `/feed/home`, `/feed/scrap`) must be registered before
    `/feed/{id}`, so a fixed path is never read as an id: the protected routes, `/feed/scrap`
    among them, go first. A request is served by the first route that matches its path and its
    method, so the protected `PUT /feed/{id}` never hides the public `GET /feed/{id}`.
    """
    app.include_router(status.router)
    app.include_router(auth.router)
    app.include_router(feed.admin_router)
    app.include_router(feed.router)
