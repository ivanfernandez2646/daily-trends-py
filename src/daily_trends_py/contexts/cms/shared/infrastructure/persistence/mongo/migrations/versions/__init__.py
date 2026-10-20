from collections.abc import Sequence

from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.migration import (  # noqa: E501
    Migration,
)
from daily_trends_py.contexts.cms.shared.infrastructure.persistence.mongo.migrations.versions import (  # noqa: E501
    m0001_feeds_indexes,
)

# Applied in this order. Append new migrations; never reorder, rename or edit an applied one.
MIGRATIONS: Sequence[Migration] = [Migration.from_module(m0001_feeds_indexes)]
