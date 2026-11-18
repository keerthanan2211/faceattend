"""
Face templates are encrypted at rest with AES-256-GCM, so a copied database file
reveals nothing biometric without the server's TEMPLATE_KEY.
"""

import base64
import os
import struct
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings

NONCE_BYTES = 12


class TemplateKeyError(RuntimeError):
    """TEMPLATE_KEY is missing or malformed."""


class TemplateCipher:
    def __init__(self, key: bytes):
        if len(key) != 32:
            raise TemplateKeyError("TEMPLATE_KEY must decode to exactly 32 bytes")
        self._aes = AESGCM(key)

    def encrypt(self, vector: list[float], context: bytes = b"face-template") -> bytes:
        nonce = os.urandom(NONCE_BYTES)
        plain = struct.pack(f"<{len(vector)}f", *vector)
        return nonce + self._aes.encrypt(nonce, plain, context)

    def decrypt(self, blob: bytes, context: bytes = b"face-template") -> list[float]:
        nonce, sealed = blob[:NONCE_BYTES], blob[NONCE_BYTES:]
        plain = self._aes.decrypt(nonce, sealed, context)  # raises if tampered with
        return list(struct.unpack(f"<{len(plain) // 4}f", plain))


@lru_cache
def get_cipher() -> TemplateCipher:
    raw = get_settings().template_key
    if not raw:
        raise TemplateKeyError("TEMPLATE_KEY is not set. See backend/.env.example for how to generate one.")
    try:
        return TemplateCipher(base64.b64decode(raw))
    except ValueError as exc:
        raise TemplateKeyError("TEMPLATE_KEY must be base64-encoded") from exc
