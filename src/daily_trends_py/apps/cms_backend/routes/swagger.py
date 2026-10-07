from pathlib import Path

from fastapi import APIRouter
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse

OPENAPI_DOCUMENT = Path(__file__).resolve().parents[5] / "docs" / "openapi.yml"

router = APIRouter()


@router.get("/")
async def get_swagger_ui() -> HTMLResponse:
    return get_swagger_ui_html(openapi_url="/openapi.yml", title="Daily trends")


@router.get("/openapi.yml")
async def get_openapi_document() -> FileResponse:
    return FileResponse(OPENAPI_DOCUMENT, media_type="application/yaml")
