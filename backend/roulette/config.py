"""Application settings, read from environment variables."""

import os

DEFAULT_DATABASE_URL = "postgresql://roulette:roulette@localhost:5433/roulette"
DEFAULT_TEST_DATABASE_URL = "postgresql://roulette:roulette@localhost:5433/roulette_test"


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


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = sqlalchemy_url(
        os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    )
