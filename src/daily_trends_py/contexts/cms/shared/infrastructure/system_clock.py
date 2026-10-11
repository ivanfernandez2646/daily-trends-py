from datetime import datetime, tzinfo


class SystemClock:
    def __init__(self, timezone: tzinfo) -> None:
        self._timezone = timezone

    def now(self) -> datetime:
        return datetime.now(self._timezone)
