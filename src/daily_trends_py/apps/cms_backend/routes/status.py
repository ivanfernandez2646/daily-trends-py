from fastapi import APIRouter, Response, status

router = APIRouter()


@router.get("/status")
async def get_status() -> Response:
    return Response(status_code=status.HTTP_200_OK)
