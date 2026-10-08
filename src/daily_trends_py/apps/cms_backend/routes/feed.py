from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from daily_trends_py.apps.cms_backend.controllers import run_controller
from daily_trends_py.apps.cms_backend.request_body import parse_body
from daily_trends_py.contexts.cms.feeds.application.create.feed_creator import FeedCreator
from daily_trends_py.contexts.cms.feeds.application.delete.feed_deleter import FeedDeleter
from daily_trends_py.contexts.cms.feeds.application.find.feed_finder import FeedFinder
from daily_trends_py.contexts.cms.feeds.application.home.feed_home_searcher import (
    FeedHomeSearcher,
)
from daily_trends_py.contexts.cms.feeds.application.scrap.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.feeds.application.search.feed_searcher import FeedSearcher
from daily_trends_py.contexts.cms.feeds.application.update.feed_updater import FeedUpdater
from daily_trends_py.contexts.cms.feeds.domain.feed_already_exists import FeedAlreadyExists
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_not_found import FeedNotFound
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.raw_value import MISSING

router = APIRouter()


@router.get("/feed/list")
async def list_feeds(request: Request) -> Response:
    feed_searcher: FeedSearcher = request.app.state.feed_searcher

    async def action() -> Response:
        feeds = await feed_searcher.execute({"sort": {"createdAt": "desc"}})
        return JSONResponse(
            [feed.to_primitives() for feed in feeds], status_code=status.HTTP_200_OK
        )

    return await run_controller(action)


@router.get("/feed/scrap")
async def scrap_feeds(request: Request) -> Response:
    feed_scraper: FeedScraper = request.app.state.feed_scraper

    async def action() -> Response:
        await feed_scraper.execute()
        return Response(status_code=status.HTTP_200_OK)

    return await run_controller(action)


@router.get("/feed/home")
async def home_feeds(request: Request) -> Response:
    feed_home_searcher: FeedHomeSearcher = request.app.state.feed_home_searcher

    async def action() -> Response:
        feeds = await feed_home_searcher.execute()
        return JSONResponse(
            [feed.to_primitives() for feed in feeds], status_code=status.HTTP_200_OK
        )

    return await run_controller(action, [(InvalidArgumentError, status.HTTP_400_BAD_REQUEST)])


@router.put("/feed/{id}")
async def create_feed(id: str, request: Request) -> Response:
    feed_creator: FeedCreator = request.app.state.feed_creator

    body = await parse_body(request)

    async def action() -> Response:
        feed = await feed_creator.execute(
            {
                "id": id,
                "title": body.get("title", MISSING),
                "description": body.get("description", MISSING),
                "author": body.get("author", MISSING),
                "source": FeedSource.CMS,
            }
        )
        return JSONResponse(feed.to_primitives(), status_code=status.HTTP_201_CREATED)

    return await run_controller(
        action,
        [
            (FeedAlreadyExists, status.HTTP_409_CONFLICT),
            (InvalidArgumentError, status.HTTP_400_BAD_REQUEST),
        ],
    )


@router.get("/feed/{id}")
async def find_feed(id: str, request: Request) -> Response:
    feed_finder: FeedFinder = request.app.state.feed_finder

    async def action() -> Response:
        feed = await feed_finder.execute(FeedId(id))
        return JSONResponse(feed.to_primitives(), status_code=status.HTTP_200_OK)

    return await run_controller(
        action,
        [
            (FeedNotFound, status.HTTP_404_NOT_FOUND),
            (InvalidArgumentError, status.HTTP_400_BAD_REQUEST),
        ],
    )


@router.delete("/feed/{id}")
async def delete_feed(id: str, request: Request) -> Response:
    feed_deleter: FeedDeleter = request.app.state.feed_deleter

    async def action() -> Response:
        await feed_deleter.execute(FeedId(id))
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return await run_controller(
        action,
        [
            (FeedNotFound, status.HTTP_404_NOT_FOUND),
            (InvalidArgumentError, status.HTTP_400_BAD_REQUEST),
        ],
    )


@router.patch("/feed/{id}")
async def update_feed(id: str, request: Request) -> Response:
    feed_updater: FeedUpdater = request.app.state.feed_updater

    body = await parse_body(request)

    async def action() -> Response:
        feed = await feed_updater.execute(
            {
                "id": id,
                "title": body.get("title", MISSING),
                "description": body.get("description", MISSING),
            }
        )
        return JSONResponse(feed.to_primitives(), status_code=status.HTTP_200_OK)

    return await run_controller(
        action,
        [
            (FeedNotFound, status.HTTP_404_NOT_FOUND),
            (InvalidArgumentError, status.HTTP_400_BAD_REQUEST),
        ],
    )
