"""Password hashing and session tokens: the only place that touches raw secrets.

- Passwords: Argon2id (memory-hard, salted automatically). We store only the hash.
- Session tokens: 256 random bits. The client keeps the token; the database keeps only its
  SHA-256, so a leaked database contains no usable tokens.
"""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()

# Verified against when an email is unknown, so "no such user" takes as long as
# "wrong password" and response times do not reveal which emails exist.
_DUMMY_HASH = _hasher.hash("campusmate-timing-equaliser")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True when the hash was made with older/weaker parameters than the current ones."""
    return _hasher.check_needs_rehash(password_hash)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
