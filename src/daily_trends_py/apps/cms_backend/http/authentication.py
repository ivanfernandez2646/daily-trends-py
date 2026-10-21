from dishka import AsyncContainer
from fastapi import Request
from fastapi.security import HTTPBearer

from daily_trends_py.contexts.cms.users.domain.access_token_verifier import AccessTokenVerifier
from daily_trends_py.contexts.cms.users.domain.errors import MissingAccessToken
from daily_trends_py.contexts.cms.users.domain.verified_access_token import VerifiedAccessToken

# Reads `Authorization: Bearer <token>`, ignoring the case of the scheme, and declares the scheme
# in OpenAPI. It answers `None` instead of failing, so the app answers its own 401.
BEARER = HTTPBearer(auto_error=False, scheme_name="bearer")


async def authenticate(request: Request) -> VerifiedAccessToken:
    """The administrator behind the request's access token, and when the token expires.

    Raises `MissingAccessToken` without a bearer token, and `InvalidAccessToken` for a token that
    is not valid or has expired.
    """
    credentials = await BEARER(request)
    if credentials is None:
        raise MissingAccessToken()
    # dishka keeps the request's container in the untyped request state.
    container: AsyncContainer = request.state.dishka_container
    verifier = await container.get(AccessTokenVerifier)
    return verifier.verify(credentials.credentials)
