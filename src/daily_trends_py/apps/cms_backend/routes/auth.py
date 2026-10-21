from typing import Annotated

from dishka.integrations.fastapi import FromDishka
from fastapi import APIRouter, Depends, Security, status

from daily_trends_py.apps.cms_backend.http.authentication import BEARER, authenticate
from daily_trends_py.apps.cms_backend.http.json_body_route import JsonBodyRoute
from daily_trends_py.apps.cms_backend.routes.auth_schemas import (
    AccessTokenResponse,
    AdminSessionResponse,
    LoginRequest,
)
from daily_trends_py.apps.cms_backend.routes.feed_schemas import ErrorResponse
from daily_trends_py.contexts.cms.users.application.authenticate.user_authenticator import (
    UserAuthenticator,
)
from daily_trends_py.contexts.cms.users.application.find_session.admin_session_finder import (
    AdminSessionFinder,
)
from daily_trends_py.contexts.cms.users.domain.verified_access_token import VerifiedAccessToken

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


# No body to read first, so a dependency authenticates before anything else can fail.
@router.get(
    "/auth/me",
    dependencies=[Security(BEARER)],
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse,
            "description": "Missing, invalid or expired access token, or its user no longer exists",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Unexpected error, such as an invalid stored user",
        },
    },
)
async def admin_session(
    token: Annotated[VerifiedAccessToken, Depends(authenticate)],
    finder: FromDishka[AdminSessionFinder],
) -> AdminSessionResponse:
    """The administrator behind the bearer access token, and when the token expires."""
    return AdminSessionResponse.from_admin_session(await finder.execute(token))
