import base64
import json

import pytest

from daily_trends_py.apps.cms_backend.routes.feed_cursor import decode_cursor, encode_cursor
from daily_trends_py.contexts.cms.feeds.domain.feed_position import FeedPosition
from tests.contexts.cms.feeds.domain.feed_created_at_mother import FeedCreatedAtMother
from tests.contexts.cms.feeds.domain.feed_id_mother import FeedIdMother

ID = "9d5b8b0e-4b0e-4c55-9f0e-2a4a1d6b3c11"


def _cursor(document: object) -> str:
    return base64.urlsafe_b64encode(json.dumps(document).encode()).decode()


def test_a_cursor_decodes_to_the_position_it_encodes() -> None:
    position = FeedPosition(
        created_at=FeedCreatedAtMother.create("2026-10-21T10:15:30.250Z"),
        id=FeedIdMother.create(ID),
    )

    assert decode_cursor(encode_cursor(position)) == position


def test_a_cursor_is_url_safe_base64_of_the_utc_date_and_the_id() -> None:
    position = FeedPosition(
        created_at=FeedCreatedAtMother.create("2026-10-21T12:15:30.250+02:00"),
        id=FeedIdMother.create(ID),
    )

    cursor = encode_cursor(position)

    assert json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))) == {
        "created_at": "2026-10-21T10:15:30.250000Z",
        "id": ID,
    }
    assert set(cursor) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


@pytest.mark.parametrize(
    "cursor",
    [
        pytest.param("abc", id="not base64"),
        pytest.param("ñ", id="not ascii"),
        pytest.param(base64.urlsafe_b64encode(b"\xff\xfe").decode(), id="not utf-8"),
        pytest.param(base64.urlsafe_b64encode(b"not json").decode(), id="not json"),
        pytest.param(_cursor(["2026-10-21T10:15:30Z", ID]), id="not an object"),
        pytest.param(_cursor({"created_at": "2026-10-21T10:15:30Z"}), id="no id"),
        pytest.param(_cursor({"id": ID}), id="no date"),
        pytest.param(_cursor({"created_at": 1, "id": ID}), id="date not a string"),
        pytest.param(_cursor({"created_at": "yesterday", "id": ID}), id="not a date"),
        pytest.param(_cursor({"created_at": "2026-10-21T10:15:30", "id": ID}), id="naive date"),
        pytest.param(_cursor({"created_at": "2026-10-21T10:15:30+02:00", "id": ID}), id="not utc"),
        pytest.param(_cursor({"created_at": "2026-10-21T10:15:30Z", "id": "1"}), id="not a uuid"),
        pytest.param(
            _cursor({"created_at": "2026-10-21T10:15:30Z", "id": 1}), id="id not a string"
        ),
    ],
)
def test_rejects_a_cursor_it_did_not_encode(cursor: str) -> None:
    with pytest.raises(ValueError) as error:
        decode_cursor(cursor)

    assert str(error.value) == "Invalid cursor"
