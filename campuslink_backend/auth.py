"""
auth.py — tiny signed-token login helpers for CampusLink (standard library only).

A token is  <payload>.<signature>  where the payload is base64url JSON such as
{"role": "student", "student_id": 3, "exp": 1767225600} and the signature is an
HMAC-SHA256 of the payload made with SECRET. Nobody can change the role or the
student_id in a token without knowing SECRET, so the server can trust it.

DEMO SETTINGS: the default passwords and secret below are fine for a college
project. Before showing this to real users, set your own with environment
variables (PowerShell example):
    $env:CAMPUSLINK_SECRET = "some-long-random-text"
    $env:CAMPUSLINK_ADMIN_PASSWORD = "a-better-password"
"""

import base64
import hashlib
import hmac
import json
import os
import time
from dotenv import load_dotenv



load_dotenv()
SECRET = os.environ.get("CAMPUSLINK_SECRET", "campuslink-dev-secret-change-me")
TOKEN_TTL_SECONDS = 8 * 60 * 60  # a login lasts 8 hours

PASSWORDS = {
    "student":   os.environ.get("CAMPUSLINK_STUDENT_PASSWORD",   "student123"),
    "recruiter": os.environ.get("CAMPUSLINK_RECRUITER_PASSWORD", "recruiter123"),
    "admin":     os.environ.get("CAMPUSLINK_ADMIN_PASSWORD",     "admin123"),
}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload_b64: str) -> str:
    return _b64(hmac.new(SECRET.encode(), payload_b64.encode(), hashlib.sha256).digest())


def check_password(role: str, password: str) -> bool:
    expected = PASSWORDS.get(role)
    if expected is None:
        return False
    return hmac.compare_digest(password.encode(), expected.encode())

def hash_account_password(password: str) -> str:
    """Hash an individual account password using PBKDF2-SHA256."""
    salt = os.urandom(16)
    iterations = 310_000

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )

    return (
        f"pbkdf2_sha256${iterations}$"
        f"{_b64(salt)}${_b64(password_hash)}"
    )


def verify_account_password(password: str, stored_hash: str) -> bool:
    """Verify a password against its stored PBKDF2 hash."""
    try:
        algorithm, iterations, salt_text, hash_text = stored_hash.split("$")

        if algorithm != "pbkdf2_sha256":
            return False

        expected_hash = _unb64(hash_text)
        salt = _unb64(salt_text)

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )

        return hmac.compare_digest(actual_hash, expected_hash)
    except (ValueError, TypeError):
        return False

def create_token(claims: dict, ttl: int = TOKEN_TTL_SECONDS) -> str:
    body = dict(claims, exp=int(time.time()) + ttl)
    payload = _b64(json.dumps(body, separators=(",", ":")).encode())
    return payload + "." + _sign(payload)


def verify_token(token: str):
    """Returns the claims dict if the token is genuine and not expired, else None."""
    try:
        payload, signature = token.split(".")
        if not hmac.compare_digest(signature, _sign(payload)):
            return None
        claims = json.loads(_unb64(payload))
        if claims.get("exp", 0) < time.time():
            return None
        return claims
    except Exception:
        return None
