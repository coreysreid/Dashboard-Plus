"""Proof that an address is the real Dashboard Plus, worked out from a key without ever sending it (decision 0086)."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets

VERSION = "dashboard-plus-hello-v1"
ID_PREFIX = "dph-id:"         # the public name of a key: told to anyone, gives nothing away
SECRET_PREFIX = "dph-hello:"  # the shared secret for the proof: never sent by either side
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def fingerprint(key: str) -> str:
    """The SHA-256 of a key, exactly as Dashboard keeps it in data/secrets/helper_keys.json."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def key_name(fp: str) -> str:
    """The public name of a key, from its fingerprint. Both sides can work it out; nobody can work back from it."""
    return hashlib.sha256((ID_PREFIX + fp).encode("ascii")).hexdigest()


def shared_secret(fp: str) -> bytes:
    """What the proof is signed with: known only to the key's holder and the Dashboard that made the key."""
    return hashlib.sha256((SECRET_PREFIX + fp).encode("ascii")).digest()


def proof(secret: bytes, nonce: str, host: str) -> str:
    """HMAC-SHA256 over the version, the caller's fresh nonce and the exact host:port it thinks it is talking to."""
    return hmac.new(secret, f"{VERSION}|{nonce}|{host}".encode("ascii"), hashlib.sha256).hexdigest()


def new_nonce() -> str:
    return secrets.token_hex(32)


def answer(fingerprints, name: str, nonce: str, host: str, unknown_secret: bytes) -> str:
    """Dashboard's side: the proof for the key called `name`.

    Every known key is looked at, so timing says nothing. A name that is not a working key gets a proof made
    with a secret only this process holds: the same shape, but useless to whoever asked."""
    found = None
    for fp in fingerprints:
        if hmac.compare_digest(key_name(fp), name):
            found = fp
    secret = shared_secret(found) if found else hmac.new(unknown_secret, name.encode("ascii"), hashlib.sha256).digest()
    return proof(secret, nonce, host)


def matches(key: str, nonce: str, host: str, answered) -> bool:
    """The connector's side: True only if `answered` is the proof only the real Dashboard could have made."""
    if not isinstance(answered, str) or not HEX64.match(answered):
        return False
    return hmac.compare_digest(proof(shared_secret(fingerprint(key)), nonce, host), answered)
