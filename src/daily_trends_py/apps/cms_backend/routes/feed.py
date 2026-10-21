from typing import Annotated

from dishka.integrations.fastapi import FromDishka
from fastapi import APIRouter, Depends, Query, Response, Security, status
from fastapi.exceptions import RequestValidationError

from daily_trends_py.apps.cms_backend.http.admin_route import AdminRoute
from daily_trends_py.apps.cms_backend.http.authentication import BEARER
from daily_trends_py.apps.cms_backend.http.json_body_route import JsonBodyRoute
from daily_trends_py.apps.cms_backend.routes.feed_cursor import decode_cursor, encode_cursor
from daily_trends_py.apps.cms_backend.routes.feed_schemas import (
    CreateFeedRequest,
    ErrorResponse,
    FeedPageResponse,
    FeedResponse,
    SearchText,
    UpdateFeedRequest,
)
from daily_trends_py.contexts.cms.feeds.application.create.feed_creator import FeedCreator
from daily_trends_py.contexts.cms.feeds.application.delete.feed_deleter import FeedDeleter
from daily_trends_py.contexts.cms.feeds.application.find.feed_finder import FeedFinder
from daily_trends_py.contexts.cms.feeds.application.home.feed_home_searcher import (
    FeedHomeSearcher,
)
from daily_trends_py.contexts.cms.feeds.application.scrape.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.feeds.application.search.feed_searcher import FeedSearcher
from daily_trends_py.contexts.cms.feeds.application.update.feed_updater import FeedUpdater
from daily_trends_py.contexts.cms.feeds.domain.feed_position import FeedPosition
from daily_trends_py.contexts.cms.feeds.domain.value_objects import (
    FeedCategory,
    FeedId,
    FeedSource,
)

router = APIRouter(route_class=JsonBodyRoute, tags=["feeds"])

_ERROR_DESCRIPTIONS = {
    status.HTTP_400_BAD_REQUEST: "Invalid request: the body, the id or a value",
    status.HTTP_401_UNAUTHORIZED: "Missing, invalid or expired access token",
    status.HTTP_404_NOT_FOUND: "No feed has this id",
    status.HTTP_409_CONFLICT: "A feed with this id already exists",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "Unexpected error, such as an invalid stored feed",
}


def _errors(*status_codes: int) -> dict[int | str, dict[str, object]]:
    return {
        status_code: {"model": ErrorResponse, "description": _ERROR_DESCRIPTIONS[status_code]}
        for status_code in status_codes
    }


# The routes that write feeds: only administrators, with a bearer access token, can call them.
admin_router = APIRouter(
    route_class=AdminRoute,
    tags=["feeds"],
    dependencies=[Security(BEARER)],
    responses=_errors(status.HTTP_401_UNAUTHORIZED),
)


def _after(
    cursor: Annotated[
        str | None, Query(description="The `next_cursor` of a previous page; absent for the first.")
    ] = None,
) -> FeedPosition | None:
    if cursor is None:
        return None
    try:
        return decode_cursor(cursor)
    except ValueError:
        raise RequestValidationError(
            [
                {
                    "type": "invalid_cursor",
                    "loc": ("query", "cursor"),
                    "msg": "Invalid cursor",
                    "input": cursor,
                }
            ]
        ) from None


@router.get("/feed/list", responses=_errors(400, 500))
async def list_feeds(
    searcher: FromDishka[FeedSearcher],
    after: Annotated[FeedPosition | None, Depends(_after)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: FeedCategory | None = None,
    source: FeedSource | None = None,
    q: Annotated[
        SearchText | None,
        Query(
            description="Words to look for in the title and the description, in Spanish: a feed"
            " matches when it has any of them, ignoring case and accents, and matching their"
            " stems but not fragments."
        ),
    ] = None,
) -> FeedPageResponse:
    """A page of the feeds, or only those of `category`, of `source` and with any word of `q`,
    newest first.

    Feeds that share their creation date are ordered by id. Feeds saved while a client browses
    never shift its next pages: they appear on a new first page.
    """
    page = await searcher.execute(
        limit=limit, after=after, category=category, source=source, text=q
    )
    return FeedPageResponse(
        items=[FeedResponse.from_feed(feed) for feed in page.feeds],
        next_cursor=None if page.next is None else encode_cursor(page.next),
    )


@admin_router.get("/feed/scrap", responses=_errors(500))
async def scrap_feeds(scraper: FromDishka[FeedScraper]) -> list[FeedResponse]:
    """Scrape the external front pages and answer the feeds this run stored.
    It first waits for a scraping run in progress, such as a scheduled one, and then usually stores
    nothing new."""
    return [FeedResponse.from_feed(feed) for feed in await scraper.execute()]


@router.get("/feed/home", responses=_errors(500))
async def home_feeds(home_searcher: FromDishka[FeedHomeSearcher]) -> list[FeedResponse]:
    """The 2 newest feeds of each external source, filled with the newest of any of them up to 10,
    newest first."""
    return [FeedResponse.from_feed(feed) for feed in await home_searcher.execute()]


@admin_router.put(
    "/feed/{id}", status_code=status.HTTP_201_CREATED, responses=_errors(400, 409, 500)
)
async def create_feed(
    id: str, body: CreateFeedRequest, creator: FromDishka[FeedCreator]
) -> FeedResponse:
    """Create a CMS feed with the given id."""
    feed = await creator.execute(
        id=id,
        title=body.title,
        description=body.description,
        author=body.author,
        source=FeedSource.CMS,
        category=body.category,
    )
    return FeedResponse.from_feed(feed)


@router.get("/feed/{id}", responses=_errors(400, 404, 500))
async def find_feed(id: str, finder: FromDishka[FeedFinder]) -> FeedResponse:
    return FeedResponse.from_feed(await finder.execute(FeedId(id)))


@admin_router.delete(
    "/feed/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_errors(400, 404, 500),
)
async def delete_feed(id: str, deleter: FromDishka[FeedDeleter]) -> None:
    await deleter.execute(FeedId(id))


@admin_router.patch("/feed/{id}", responses=_errors(400, 404, 500))
async def update_feed(
    id: str, body: UpdateFeedRequest, updater: FromDishka[FeedUpdater]
) -> FeedResponse:
    """Change only the fields that are sent; `null` clears the description."""
    return FeedResponse.from_feed(await updater.execute(id, **body))
