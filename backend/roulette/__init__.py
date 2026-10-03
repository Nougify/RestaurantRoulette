"""RestaurantRoulette backend: a Flask API over a PostGIS database of restaurants."""

from flask import Flask

from .config import Config
from .extensions import cors, db, limiter, migrate


def create_app(config_object: type = Config) -> Flask:
    """Build and configure a Flask application (the "app factory" pattern)."""
    # This is a JSON API with no files of its own to serve, so the /static route is off.
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_object)

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    # Browsers block a page on one origin from calling an API on another unless the API
    # says that origin is allowed. Only the frontend's origins are, and only for /api.
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    # Imported for its side effect: registering the tables on `db.metadata`.
    from . import models  # noqa: F401
    from .api import register_api
    from .errors import register_error_handlers
    from .importer import register_commands

    register_api(app)
    register_error_handlers(app)
    register_commands(app)

    if app.config["SECRET_KEY_IS_TEMPORARY"]:
        app.logger.warning(
            "SECRET_KEY is not set: using a temporary key, so login tokens will stop "
            "working when the server restarts. Set SECRET_KEY in the environment."
        )

    return app
