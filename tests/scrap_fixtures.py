from collections.abc import Collection
from pathlib import Path

import httpx

_FIXTURES = Path(__file__).parent / "fixtures" / "scrap"
_FRONT_PAGES = {"www.elespanol.com": "el_espanol.html"}


class FrontPagesTransport(httpx.MockTransport):
    """Serves the recorded front pages by host and keeps every request it receives."""

    def __init__(self, *, failing_hosts: Collection[str] = ()) -> None:
        super().__init__(self._handle)
        self._failing_hosts = failing_hosts
        self.requests: list[httpx.Request] = []

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        host = request.url.host
        if host in self._failing_hosts:
            raise httpx.ConnectError(f"Cannot connect to {host}", request=request)
        fixture = _FRONT_PAGES.get(host)
        if fixture is None:
            return httpx.Response(404)
        return httpx.Response(200, content=(_FIXTURES / fixture).read_bytes())
