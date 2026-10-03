"""Application settings, read from environment variables."""

import os
import secrets
from datetime import timedelta

DEFAULT_DATABASE_URL = "postgresql://roulette:roulette@localhost:5433/roulette"
DEFAULT_TEST_DATABASE_URL = "postgresql://roulette:roulette@localhost:5433/roulette_test"

# Where the Vite dev server runs; the deployed frontend's origin is set through CORS_ORIGINS.
DEFAULT_CORS_ORIGINS = "http://localhost:5173"


def sqlalchemy_url(url: str) -> str:
    """Return `url` with the scheme that makes SQLAlchemy use the psycopg 3 driver.

    Hosting providers hand out `postgres://` or `postgresql://` URLs, which SQLAlchemy
    would either reject or route to the older psycopg2 driver.
    """
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


class Config:
    SQLALCHEMY_DATABASE_URI = sqlalchemy_url(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))

    # Signs login tokens. There is deliberately no fixed fallback: a key committed to the
    # repository would let anyone forge a token. Without SECRET_KEY set, a random key is
    # made at startup, which is safe but logs everyone out whenever the server restarts.
    SECRET_KEY = os.environ.get("SECRET_KEY")
    # An empty value (`SECRET_KEY=` left blank in .env) counts as not set.
    SECRET_KEY_IS_TEMPORARY = not SECRET_KEY
    if SECRET_KEY_IS_TEMPORARY:
        SECRET_KEY = secrets.token_hex(32)

    TOKEN_LIFETIME = timedelta(days=7)

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
        if origin.strip()
    ]

    # Flask-Limiter: counters are kept in this process's memory.
    RATELIMIT_STORAGE_URI = "memory://"
    AUTH_RATE_LIMIT = "10 per minute"


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = sqlalchemy_url(
        os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    )
    SECRET_KEY = "test-secret-key-that-is-long-enough-for-hs256"
    SECRET_KEY_IS_TEMPORARY = False
    # Off so ordinary tests can log in freely; the rate-limit test turns it on.
    RATELIMIT_ENABLED = False
