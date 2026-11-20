"""Call the helper API on this computer: check it is the real Dashboard first, then send the key down that connection only."""
from __future__ import annotations

import http.client
import json
import socket
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from dashboard import __version__
from dashboard.core import hello, helper_address

TIMEOUT = 15  # seconds
MAX_ANSWER = 4 * 1024 * 1024  # bytes; a full page of records is far smaller
MAX_HELLO_ANSWER = 1024  # bytes; Dashboard's answer to the check is about 120
WHERE_ADDRESS = ("This assistant uses the copied address. Dashboard Plus chooses a new one each time it opens; "
                 "copy the current address again from Settings → Helpers.")  # manual address mode (0092)
NOT_REACHED = "Dashboard Plus could not be reached. Is it open on this computer? " + WHERE_ADDRESS
NOT_ANSWERING = ("Dashboard Plus is not answering at the address in its connection file. Open it again and try "
                 "once more. The key was not sent.")
NOT_DASHBOARD = ("This address is not Dashboard Plus, or it is an old address. Open Dashboard Plus and copy the "
                 "address again from Settings → Helpers. If the address is right, this helper's key may have been "
                 "turned off: make a new one there. The key was not sent.")


@dataclass
class Answer:
    """What the API said: its status and JSON body, or (status 0) a plain reason it could not be reached."""
    status: int
    body: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


def _plain(status: int, message: str, code: str = "connector") -> Answer:
    return Answer(status, {"error": code, "message": message})


def _headers(**extra) -> dict:
    return {"Accept": "application/json", "User-Agent": f"dashboard-plus-connector/{__version__}", **extra}


def call_via_file(address_file: str, key: str, method: str, path: str, body: dict | None = None,
                  timeout: float = TIMEOUT) -> Answer:
    """Read Dashboard's address file now, then `call` the address it gives (decision 0092). Never raises.

    The file is read again for every call, because the assistant's app may keep this connector running while
    Dashboard closes and opens on a new port. Nothing about a previous call is remembered: no address and no
    passed check. A missing or wrong file stops here, before anything is contacted."""
    base, code, problem = helper_address.read(address_file)
    if problem:
        return _plain(0, problem, code)
    return call(base, key, method, path, body, timeout, not_reached=NOT_ANSWERING)


def call(base: str, key: str, method: str, path: str, body: dict | None = None,
         timeout: float = TIMEOUT, not_reached: str = NOT_REACHED) -> Answer:
    """Send one request to `base` + `path` and return the answer. Never raises for network or API problems.

    First, on a new connection and without the key, ask the program at that address to prove it is the
    Dashboard Plus that made this key (decision 0086). Only if it does is the request sent, with the key,
    down that same connection, so nothing can step in between the check and the key. `path` is built by the
    connector from a fixed list of routes, never taken from an assistant. There is no proxy (http.client
    never uses one) and redirects are never followed."""
    parts = urlsplit(base)
    host, port, prefix = parts.hostname, parts.port, parts.path.rstrip("/")
    for _attempt in range(2):
        connection = http.client.HTTPConnection(host, port, timeout=timeout)
        try:
            refusal = _check(connection, key, f"{host}:{port}", prefix)
            if refusal is not None:
                return refusal  # the key was never sent
            connection.auto_open = 0  # never reconnect on its own: a new connection would not be checked
            try:
                return _send(connection, key, method, prefix + path, body)
            except http.client.NotConnected:
                continue  # Dashboard closed the checked connection before the key went: check again
        except (TimeoutError, socket.timeout):
            return _plain(0, "Dashboard Plus did not answer in time. If this was a suggestion, try again with the "
                             "same request_key: it cannot be added twice.", "timed_out")
        except (http.client.HTTPException, OSError, ValueError):
            return _plain(0, not_reached, "not_reachable")
        finally:
            connection.close()
    return _plain(0, not_reached, "not_reachable")


def _check(connection: http.client.HTTPConnection, key: str, host: str, prefix: str) -> Answer | None:
    """Ask for proof that this is the real Dashboard Plus. None if it proved it; otherwise the refusal.

    Sent: a fresh random nonce and the key's public name, which nobody can work back to the key."""
    nonce = hello.new_nonce()
    payload = json.dumps({"key_name": hello.key_name(hello.fingerprint(key)), "nonce": nonce})
    connection.request("POST", prefix + "/hello", body=payload.encode("ascii"),
                       headers=_headers(**{"Content-Type": "application/json"}))
    response = connection.getresponse()
    raw = response.read(MAX_HELLO_ANSWER + 1)
    if response.status == 429:  # our own words: this program has not proved what it is yet
        return _plain(0, "Dashboard Plus is getting too many connection checks. Wait a minute, then try again.",
                      "too_many_requests")
    try:
        said = json.loads(raw.decode("utf-8")) if len(raw) <= MAX_HELLO_ANSWER else None
    except (UnicodeDecodeError, ValueError):
        said = None
    if (response.status == 200 and isinstance(said, dict) and said.get("hello") == hello.VERSION
            and hello.matches(key, nonce, host, said.get("proof"))):
        return None
    return _plain(0, NOT_DASHBOARD, "not_dashboard")


def _send(connection: http.client.HTTPConnection, key: str, method: str, path: str, body: dict | None) -> Answer:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = _headers(Authorization=f"Bearer {key}")
    if data is not None:
        headers["Content-Type"] = "application/json"
    connection.request(method, path, body=data, headers=headers)
    response = connection.getresponse()
    if 300 <= response.status < 400:
        return _plain(response.status, "Dashboard Plus answered with a redirect, which the connector never "
                                        "follows. Check the address in Settings, Helpers.", "redirect_refused")
    return _read(response.status, response)


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
