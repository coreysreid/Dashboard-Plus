"""Call the helper API on this computer: fixed routes only, the key only in its header, no proxy, no redirects."""
from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from dashboard import __version__

TIMEOUT = 15  # seconds
MAX_ANSWER = 4 * 1024 * 1024  # bytes; a full page of records is far smaller
WHERE_ADDRESS = ("The address changes each time Dashboard opens: copy the current one from "
                 "Settings, Helpers and update the assistant's settings.")


@dataclass
class Answer:
    """What the API said: its status and JSON body, or (status 0) a plain reason it could not be reached."""
    status: int
    body: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect: it could carry the key to another address."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _opener() -> urllib.request.OpenerDirector:
    # An empty ProxyHandler ignores HTTP_PROXY and friends, so the key never goes through a proxy.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirects())


def _plain(status: int, message: str, code: str = "connector") -> Answer:
    return Answer(status, {"error": code, "message": message})


def call(base: str, key: str, method: str, path: str, body: dict | None = None,
         timeout: float = TIMEOUT) -> Answer:
    """Send one request to `base` + `path` and return the answer. Never raises for network or API problems.

    `path` is built by the connector from a fixed list of routes, never taken from an assistant."""
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(base + path, data=data, method=method)
    request.add_header("Authorization", f"Bearer {key}")
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", f"dashboard-plus-connector/{__version__}")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with _opener().open(request, timeout=timeout) as response:
            return _read(response.status, response)
    except urllib.error.HTTPError as error:
        with error:
            if 300 <= error.code < 400:
                return _plain(error.code, "Dashboard Plus answered with a redirect, which the connector never "
                                          "follows. Check the address in Settings, Helpers.", "redirect_refused")
            return _read(error.code, error)
    except (TimeoutError, socket.timeout):
        return _plain(0, "Dashboard Plus did not answer in time. If this was a suggestion, try again with the "
                         "same request_key: it cannot be added twice.", "timed_out")
    except (urllib.error.URLError, OSError, ValueError):
        return _plain(0, "Dashboard Plus could not be reached. Is it open on this computer? " + WHERE_ADDRESS,
                      "not_reachable")


def _read(status: int, response) -> Answer:
    raw = response.read(MAX_ANSWER + 1)
    if len(raw) > MAX_ANSWER:
        return _plain(status if status >= 400 else 0, "Dashboard Plus sent more than the connector reads at once. "
                                                     "Ask for fewer records (a smaller limit).", "too_large")
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        body = None
    if not isinstance(body, dict):
        return _plain(status if status >= 400 else 0, "The answer was not from Dashboard Plus's helper API. "
                                                     + WHERE_ADDRESS, "not_dashboard")
    return Answer(status, body)
