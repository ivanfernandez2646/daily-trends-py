from datetime import UTC, datetime

from dishka.integrations.fastapi import FromDishka
from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse

from daily_trends_py.apps.cms_backend.routes.feed_route import FeedRoute
from daily_trends_py.apps.cms_backend.routes.feed_schemas import (
    CreateFeedRequest,
    UpdateFeedRequest,
)
from daily_trends_py.contexts.cms.feeds.application.create.feed_creator import FeedCreator
from daily_trends_py.contexts.cms.feeds.application.delete.feed_deleter import FeedDeleter
from daily_trends_py.contexts.cms.feeds.application.find.feed_finder import FeedFinder
from daily_trends_py.contexts.cms.feeds.application.home.feed_home_searcher import (
    FeedHomeSearcher,
)
from daily_trends_py.contexts.cms.feeds.application.scrap.feed_scraper import FeedScraper
from daily_trends_py.contexts.cms.feeds.application.search.feed_searcher import FeedSearcher
from daily_trends_py.contexts.cms.feeds.application.update.feed_updater import FeedUpdater
from daily_trends_py.contexts.cms.feeds.domain.feed import Feed
from daily_trends_py.contexts.cms.feeds.domain.feed_criteria import FeedCriteria
from daily_trends_py.contexts.cms.feeds.domain.feed_id import FeedId
from daily_trends_py.contexts.cms.feeds.domain.feed_source import FeedSource
from daily_trends_py.contexts.cms.shared.domain.criteria import Order

router = APIRouter(route_class=FeedRoute)

LIST_CRITERIA = FeedCriteria(order=Order("created_at", "desc"))


def _json_date(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _feed_json(feed: Feed) -> dict[str, object]:
    primitives = feed.to_primitives()
    return {
        **primitives,
        "createdAt": _json_date(primitives["createdAt"]),
        "updatedAt": _json_date(primitives["updatedAt"]),
    }


@router.get("/feed/list")
async def list_feeds(searcher: FromDishka[FeedSearcher]) -> Response:
    feeds = await searcher.execute(LIST_CRITERIA)
    return JSONResponse([_feed_json(feed) for feed in feeds], status_code=status.HTTP_200_OK)


@router.get("/feed/scrap")
async def scrap_feeds(scraper: FromDishka[FeedScraper]) -> Response:
    feeds = await scraper.execute()
    return JSONResponse([_feed_json(feed) for feed in feeds], status_code=status.HTTP_200_OK)


@router.get("/feed/home")
async def home_feeds(home_searcher: FromDishka[FeedHomeSearcher]) -> Response:
    feeds = await home_searcher.execute()
    return JSONResponse([_feed_json(feed) for feed in feeds], status_code=status.HTTP_200_OK)


@router.put("/feed/{id}")
async def create_feed(
    id: str, body: CreateFeedRequest, creator: FromDishka[FeedCreator]
) -> Response:
    feed = await creator.execute(
        {
            "id": id,
            "title": body.title,
            "description": body.description,
            "author": body.author,
            "source": FeedSource.CMS,
        }
    )
    return JSONResponse(_feed_json(feed), status_code=status.HTTP_201_CREATED)


@router.get("/feed/{id}")
async def find_feed(id: str, finder: FromDishka[FeedFinder]) -> Response:
    feed = await finder.execute(FeedId(id))
    return JSONResponse(_feed_json(feed), status_code=status.HTTP_200_OK)


@router.delete("/feed/{id}")
async def delete_feed(id: str, deleter: FromDishka[FeedDeleter]) -> Response:
    await deleter.execute(FeedId(id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/feed/{id}")
async def update_feed(
    id: str, body: UpdateFeedRequest, updater: FromDishka[FeedUpdater]
) -> Response:
    feed = await updater.execute({"id": id, **body})
    return JSONResponse(_feed_json(feed), status_code=status.HTTP_200_OK)
