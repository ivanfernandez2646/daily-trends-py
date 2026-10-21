from typing import Protocol

from daily_trends_py.contexts.cms.users.domain.access_token import AccessToken
from daily_trends_py.contexts.cms.users.domain.value_objects import UserId


class AccessTokenIssuer(Protocol):
    def issue(self, user_id: UserId) -> AccessToken: ...
