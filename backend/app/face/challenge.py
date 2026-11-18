"""
Stateless, signed, single-use liveness challenges.

The token carries the direction, a random nonce and an expiry, signed with HMAC-SHA256,
so it can't be forged or altered. Each nonce is recorded when used, so a captured token
can't be replayed.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time

from app.face.liveness import Direction


class ChallengeError(ValueError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue(secret: bytes, ttl_seconds: int, now: float | None = None) -> tuple[str, Direction, int]:
    direction: Direction = secrets.choice(["left", "right"])
    expires = int((now or time.time()) + ttl_seconds)
    payload = json.dumps({"d": direction, "n": secrets.token_hex(12), "e": expires}, separators=(",", ":")).encode()
    signature = hmac.new(secret, payload, hashlib.sha256).digest()
    return f"{_b64(payload)}.{_b64(signature)}", direction, expires


def verify(secret: bytes, token: str, now: float | None = None) -> tuple[str, Direction]:
    """Returns (nonce, direction) for a valid, unexpired token. Single use is enforced by the caller."""
    try:
        payload_b64, signature_b64 = token.split(".")
        payload, signature = _unb64(payload_b64), _unb64(signature_b64)
    except ValueError as exc:
        raise ChallengeError("Invalid challenge. Start the scan again.") from exc

    expected = hmac.new(secret, payload, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise ChallengeError("Invalid challenge. Start the scan again.")

    data = json.loads(payload)
    if (now or time.time()) > data["e"]:
        raise ChallengeError("The scan took too long. Start again.")
    return data["n"], data["d"]
