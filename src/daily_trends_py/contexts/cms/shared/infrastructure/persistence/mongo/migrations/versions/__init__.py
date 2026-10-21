from collections.abc import Sequence

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.migration import (  # noqa: E501
    Migration,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    m0001_feeds_indexes,
    m0002_feeds_category_and_url,
    m0003_users_indexes,
    m0004_feeds_list_indexes,
    m0005_feeds_text_index,
)

# Applied in this order. Append new migrations; never reorder, rename or edit an applied one.
MIGRATIONS: Sequence[Migration] = [
    Migration.from_module(m0001_feeds_indexes),
    Migration.from_module(m0002_feeds_category_and_url),
    Migration.from_module(m0003_users_indexes),
    Migration.from_module(m0004_feeds_list_indexes),
    Migration.from_module(m0005_feeds_text_index),
]
