"""RestaurantRoulette backend: a Flask API over a PostGIS database of restaurants."""

from flask import Flask

from .config import Config
from .extensions import db, migrate


def create_app(config_object: type = Config) -> Flask:
    """Build and configure a Flask application (the "app factory" pattern)."""
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)

    # Imported for its side effect: registering the tables on `db.metadata`.
    from . import models  # noqa: F401
    from .importer import register_commands

    register_commands(app)

    return app
