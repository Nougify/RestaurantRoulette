"""The HTTP API. Every route lives under /api."""

from flask import Blueprint, Flask

from . import auth, favourites, restaurants


def register_api(app: Flask) -> None:
    # A blueprint is a group of routes; nesting them gives every route the /api prefix.
    api = Blueprint("api", __name__, url_prefix="/api")
    api.register_blueprint(restaurants.blueprint)
    api.register_blueprint(auth.blueprint)
    api.register_blueprint(favourites.blueprint)
    app.register_blueprint(api)
