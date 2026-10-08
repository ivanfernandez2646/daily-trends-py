from collections.abc import Collection
from pathlib import Path

import httpx

_FIXTURES = Path(__file__).parent / "fixtures" / "scrap"
_FRONT_PAGES = {"www.elespanol.com": "el_espanol.html", "www.elmundo.es": "el_mundo.html"}
_REDIRECTS = {"elmundo.es": "https://www.elmundo.es/"}


class FrontPagesTransport(httpx.MockTransport):
    """Serves the front page fixtures by host, as the real sites do, and keeps every request."""

    def __init__(self, *, failing_hosts: Collection[str] = ()) -> None:
        super().__init__(self._handle)
        self._failing_hosts = failing_hosts
        self.requests: list[httpx.Request] = []

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        host = request.url.host
        if host in self._failing_hosts:
            raise httpx.ConnectError(f"Cannot connect to {host}", request=request)
        if host in _REDIRECTS:
            return httpx.Response(301, headers={"Location": _REDIRECTS[host]})
        fixture = _FRONT_PAGES.get(host)
        if fixture is None:
            return httpx.Response(404)
        return httpx.Response(200, content=(_FIXTURES / fixture).read_bytes())
