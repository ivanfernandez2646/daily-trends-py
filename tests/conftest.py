import asyncio

import pytest

from tests.mongo import TEST_MONGO_URL, mongo_unreachable_message


# Last, so the items deselected with `-m` are already gone.
@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Fail the session at once when a selected test needs a MongoDB that does not answer."""
    if config.option.collectonly or not any(
        item.get_closest_marker("integration") for item in items
    ):
        return
    message = asyncio.run(mongo_unreachable_message(TEST_MONGO_URL))
    if message is not None:
        pytest.exit(message, returncode=1)
