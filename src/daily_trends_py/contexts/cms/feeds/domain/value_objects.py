from dataclasses import dataclass
from enum import StrEnum
from typing import Never
from urllib.parse import urlsplit

from daily_trends_py.contexts.cms.shared.domain.date_time_value_object import (
    DateTimeValueObject,
    RequiredDateTimeValueObject,
)
from daily_trends_py.contexts.cms.shared.domain.invalid_argument_error import (
    InvalidArgumentError,
)
from daily_trends_py.contexts.cms.shared.domain.required_string_value_object import (
    RequiredStringValueObject,
)
from daily_trends_py.contexts.cms.shared.domain.string_value_object import StringValueObject
from daily_trends_py.contexts.cms.shared.domain.uuid_value_object import UuidValueObject


@dataclass(frozen=True)
class FeedId(UuidValueObject):
    pass


@dataclass(frozen=True)
class FeedTitle(RequiredStringValueObject):
    pass


@dataclass(frozen=True)
class FeedDescription(StringValueObject):
    pass


@dataclass(frozen=True)
class FeedAuthor(RequiredStringValueObject):
    pass


class FeedSource(StrEnum):
    CMS = "CMS"
    EL_PAIS = "EL_PAIS"
    EL_MUNDO = "EL_MUNDO"
    EL_ESPANOL = "EL_ESPANOL"
    EL_CONFIDENCIAL = "EL_CONFIDENCIAL"
    LA_RAZON = "LA_RAZON"
    LA_VANGUARDIA = "LA_VANGUARDIA"

    @classmethod
    def _missing_(cls, value: object) -> Never:
        # `Enum` raises what `_missing_` raises, so an unknown source is an invalid argument.
        raise InvalidArgumentError(f"<FeedSource> does not allow the value <{value}>")


class FeedCategory(StrEnum):
    POLITICS = "POLITICS"
    INTERNATIONAL = "INTERNATIONAL"
    ECONOMY = "ECONOMY"
    SOCIETY = "SOCIETY"
    SPORTS = "SPORTS"
    CULTURE = "CULTURE"
    TECHNOLOGY = "TECHNOLOGY"
    SCIENCE = "SCIENCE"
    HEALTH = "HEALTH"
    OPINION = "OPINION"
    OTHER = "OTHER"

    @classmethod
    def _missing_(cls, value: object) -> Never:
        raise InvalidArgumentError(f"<FeedCategory> does not allow the value <{value}>")


@dataclass(frozen=True)
class FeedUrl(StringValueObject):
    """The original article's absolute `http` or `https` URL, or `None` when there is none."""

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.value is not None and not _is_absolute_http_url(self.value):
            raise InvalidArgumentError(f"<FeedUrl> does not allow the value <{self.value}>")


def _is_absolute_http_url(value: str) -> bool:
    parts = urlsplit(value)
    return parts.scheme in ("http", "https") and parts.netloc != ""


@dataclass(frozen=True)
class FeedCreatedAt(RequiredDateTimeValueObject):
    pass


@dataclass(frozen=True)
class FeedUpdatedAt(DateTimeValueObject):
    pass
