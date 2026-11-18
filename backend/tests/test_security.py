import base64
import os

import pytest
from cryptography.exceptions import InvalidTag

from app.crypto import TemplateCipher, TemplateKeyError
from app.face import challenge

SECRET = b"s" * 32


def test_challenge_round_trip():
    token, direction, _ = challenge.issue(SECRET, 60, now=1000)
    nonce, got = challenge.verify(SECRET, token, now=1010)
    assert got == direction and len(nonce) == 24


def test_challenge_rejects_tampering_wrong_secret_and_expiry():
    token, _, _ = challenge.issue(SECRET, 60, now=1000)
    payload, sig = token.split(".")
    with pytest.raises(challenge.ChallengeError):
        challenge.verify(SECRET, f"{payload}x.{sig}", now=1010)
    with pytest.raises(challenge.ChallengeError):
        challenge.verify(b"other-secret", token, now=1010)
    with pytest.raises(challenge.ChallengeError, match="too long"):
        challenge.verify(SECRET, token, now=1061)
    with pytest.raises(challenge.ChallengeError):
        challenge.verify(SECRET, "not-a-token", now=1010)


def test_template_encryption_round_trip_and_tamper_detection():
    cipher = TemplateCipher(os.urandom(32))
    vector = [0.125, -0.5, 0.75]
    blob = cipher.encrypt(vector)
    assert cipher.decrypt(blob) == vector
    assert cipher.encrypt(vector) != blob  # fresh nonce every time
    tampered = blob[:-1] + bytes([blob[-1] ^ 1])
    with pytest.raises(InvalidTag):
        cipher.decrypt(tampered)


def test_rejects_short_keys():
    with pytest.raises(TemplateKeyError):
        TemplateCipher(base64.b64decode("c2hvcnQ="))
