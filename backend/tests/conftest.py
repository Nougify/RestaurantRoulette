"""Shared pytest fixtures. Tests run against the real PostGIS `roulette_test` database."""

import pytest
from flask_migrate import upgrade
from sqlalchemy import text

from roulette import create_app
from roulette.config import TestConfig
from roulette.extensions import db


@pytest.fixture(scope="session")
def app():
    """One app for the whole run, with the schema built by the real migrations."""
    app = create_app(TestConfig)
    with app.app_context():
        upgrade()
        yield app


@pytest.fixture(autouse=True)
def clean_tables(app):
    """Empty every table after each test so tests cannot affect one another."""
    yield
    db.session.rollback()
    db.session.execute(text("TRUNCATE favourites, users, restaurants RESTART IDENTITY CASCADE"))
    db.session.commit()
    # Discard the session so objects from this test are not cached into the next one.
    db.session.remove()
