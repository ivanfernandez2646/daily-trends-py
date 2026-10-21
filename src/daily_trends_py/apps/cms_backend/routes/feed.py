from dishka.integrations.fastapi import FromDishka
from fastapi import APIRouter, Response, status

from daily_trends_py.apps.cms_backend.http.json_body_route import JsonBodyRoute
from daily_trends_py.apps.cms_backend.routes.feed_schemas import (
    CreateFeedRequest,
    ErrorResponse,
    FeedResponse,
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
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.value_objects import (
    FeedCategory,
    FeedId,
    FeedSource,
)
from daily_trends_py.contexts.cms.shared.domain.criteria import Filter, Order

router = APIRouter(route_class=JsonBodyRoute, tags=["feeds"])

NEWEST_FIRST = Order("created_at", "desc")
LIST_CRITERIA = FeedCriteria(order=NEWEST_FIRST)

_ERROR_DESCRIPTIONS = {
    status.HTTP_400_BAD_REQUEST: "Invalid request: the body, the id or a value",
    status.HTTP_404_NOT_FOUND: "No feed has this id",
    status.HTTP_409_CONFLICT: "A feed with this id already exists",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "Unexpected error, such as an invalid stored feed",
}


def _errors(*status_codes: int) -> dict[int | str, dict[str, object]]:
    return {
        status_code: {"model": ErrorResponse, "description": _ERROR_DESCRIPTIONS[status_code]}
        for status_code in status_codes
    }


@router.get("/feed/list", responses=_errors(400, 500))
async def list_feeds(
    searcher: FromDishka[FeedSearcher], category: FeedCategory | None = None
) -> list[FeedResponse]:
    """Every feed, or only those of `category`, newest first."""
    criteria = (
        LIST_CRITERIA
        if category is None
        else FeedCriteria(filters=(Filter("category", category),), order=NEWEST_FIRST)
    )
    return [FeedResponse.from_feed(feed) for feed in await searcher.execute(criteria)]


@router.get("/feed/scrap", responses=_errors(500))
async def scrap_feeds(scraper: FromDishka[FeedScraper]) -> list[FeedResponse]:
    """Scrape the external front pages and answer the feeds this run stored."""
    return [FeedResponse.from_feed(feed) for feed in await scraper.execute()]


@router.get("/feed/home", responses=_errors(500))
async def home_feeds(home_searcher: FromDishka[FeedHomeSearcher]) -> list[FeedResponse]:
    """The 2 newest feeds of each external source, filled with the newest of any of them up to 10,
    newest first; a stale front page is refreshed in the background."""
    return [FeedResponse.from_feed(feed) for feed in await home_searcher.execute()]


@router.put("/feed/{id}", status_code=status.HTTP_201_CREATED, responses=_errors(400, 409, 500))
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


@router.delete(
    "/feed/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=_errors(400, 404, 500),
)
async def delete_feed(id: str, deleter: FromDishka[FeedDeleter]) -> None:
    await deleter.execute(FeedId(id))


@router.patch("/feed/{id}", responses=_errors(400, 404, 500))
async def update_feed(
    id: str, body: UpdateFeedRequest, updater: FromDishka[FeedUpdater]
) -> FeedResponse:
    """Change only the fields that are sent; `null` clears the description."""
    return FeedResponse.from_feed(await updater.execute(id, **body))
