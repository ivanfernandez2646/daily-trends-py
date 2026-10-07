from fastapi import APIRouter, Response, status

from daily_trends_py.apps.cms_backend.controllers import run_controller

router = APIRouter()


@router.get("/status")
async def get_status() -> Response:
    async def action() -> Response:
        return Response(status_code=status.HTTP_200_OK)

    return await run_controller(action)
