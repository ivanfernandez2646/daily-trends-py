from collections.abc import Collection
from pathlib import Path

import httpx

_FIXTURES = Path(__file__).parent / "fixtures" / "scrap"
# Fixture and declared charset, as the real sites answer.
_FRONT_PAGES = {
    "www.elespanol.com": ("el_espanol.html", "UTF-8"),
    "www.elmundo.es": ("el_mundo.html", "iso-8859-15"),
}
_REDIRECTS = {"elmundo.es": "https://www.elmundo.es/"}


class FrontPagesTransport(httpx.MockTransport):
    """Serves the front page fixtures by host, as the real sites do, and keeps every request."""

    def __init__(
        self, *, failing_hosts: Collection[str] = (), timing_out_hosts: Collection[str] = ()
    ) -> None:
        super().__init__(self._handle)
        self._failing_hosts = failing_hosts
        self._timing_out_hosts = timing_out_hosts
        self.requests: list[httpx.Request] = []

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        host = request.url.host
        if host in self._failing_hosts:
            raise httpx.ConnectError(f"Cannot connect to {host}", request=request)
        if host in self._timing_out_hosts:
            raise httpx.ReadTimeout(f"{host} never answered", request=request)
        if host in _REDIRECTS:
            return httpx.Response(301, headers={"Location": _REDIRECTS[host]})
        if host not in _FRONT_PAGES:
            return httpx.Response(404)
        fixture, charset = _FRONT_PAGES[host]
        return httpx.Response(
            200,
            headers={"Content-Type": f"text/html; charset={charset}"},
            content=(_FIXTURES / fixture).read_bytes(),
        )
