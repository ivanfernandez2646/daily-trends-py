from dataclasses import dataclass
from datetime import datetime

from daily_trends_py.contexts.cms.users.domain.value_objects import UserId


@dataclass(frozen=True)
class VerifiedAccessToken:
    """A token whose signature and expiry were checked: who it is for and until when (UTC)."""

    user_id: UserId
    expires_at: datetime
