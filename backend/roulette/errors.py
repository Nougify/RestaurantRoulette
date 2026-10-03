"""One JSON shape for every error the API returns.

    {"error": {"code": "validation_error", "message": "...", "details": [...]}}

`code` is a stable machine-readable value for the frontend to branch on; `message` is for
people; `details` is only present for validation errors, one entry per rejected field.
"""

from flask import Flask, jsonify
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """Raise anywhere in a request to end it with a JSON error response."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def error_response(status: int, code: str, message: str, details: list | None = None):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return jsonify(error=error), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return error_response(error.status, error.code, error.message)

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        details = [
            {"field": ".".join(str(part) for part in problem["loc"]), "message": problem["msg"]}
            for problem in error.errors()
        ]
        return error_response(422, "validation_error", "Some values are not valid.", details)

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        # Flask's own errors (404 unknown URL, 405 wrong method, 429 rate limited...) would
        # otherwise be HTML pages.
        code = error.name.lower().replace(" ", "_")
        return error_response(error.code, code, error.description)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        # Log the real cause for the developer; tell the client nothing about internals.
        app.logger.exception("Unhandled error")
        return error_response(500, "internal_error", "Something went wrong on the server.")
