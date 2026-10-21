from dishka.integrations.fastapi import FromDishka
from fastapi import APIRouter, status

from daily_trends_py.apps.cms_backend.http.json_body_route import JsonBodyRoute
from daily_trends_py.apps.cms_backend.routes.auth_schemas import AccessTokenResponse, LoginRequest
from daily_trends_py.apps.cms_backend.routes.feed_schemas import ErrorResponse
from daily_trends_py.contexts.cms.users.application.authenticate.user_authenticator import (
    UserAuthenticator,
)

router = APIRouter(route_class=JsonBodyRoute, tags=["auth"])


@router.post(
    "/auth/login",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid body"},
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Unknown email or wrong password, answered the same way",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Unexpected error, such as an invalid stored user",
        },
    },
)
async def login(
    body: LoginRequest, authenticator: FromDishka[UserAuthenticator]
) -> AccessTokenResponse:
    """Exchange an administrator's email and password for a bearer access token."""
    token = await authenticator.execute(email=body.email, password=body.password)
    return AccessTokenResponse.from_access_token(token)
