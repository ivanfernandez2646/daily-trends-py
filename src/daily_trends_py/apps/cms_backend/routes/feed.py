from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from daily_trends_py.apps.cms_backend.controllers import run_controller
from daily_trends_py.contexts.cms.feeds.application.find.feed_finder import FeedFinder
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_not_found import FeedNotFound
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)

router = APIRouter()


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
