"""Accounts: register, log in, and "who am I"."""

from flask import Blueprint, current_app, g, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..errors import ApiError
from ..extensions import db, limiter
from ..models import User
from ..schemas import Credentials, Registration, user_json
from ..security import DUMMY_HASH, create_token, hash_password, login_required, verify_password

blueprint = Blueprint("auth", __name__, url_prefix="/auth")

# Slows down password guessing and mass sign-ups. Read from config on each request.
auth_rate_limit = limiter.limit(lambda: current_app.config["AUTH_RATE_LIMIT"])


def json_body() -> dict:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError(400, "invalid_json", "The request body must be a JSON object.")
    return body


def session_json(user: User) -> dict:
    return {"token": create_token(user), "user": user_json(user)}


@blueprint.post("/register")
@auth_rate_limit
def register():
    data = Registration.model_validate(json_body())
    user = User(email=data.email, password_hash=hash_password(data.password))
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        # The unique constraint is the check. Looking the email up first would leave a gap
        # in which two simultaneous requests could both pass.
        db.session.rollback()
        raise ApiError(409, "email_taken", "An account with this email already exists.") from None
    return session_json(user), 201


@blueprint.post("/login")
@auth_rate_limit
def login():
    data = Credentials.model_validate(json_body())
    user = db.session.scalar(select(User).where(User.email == data.email))
    password_matches = verify_password(user.password_hash if user else DUMMY_HASH, data.password)
    if user is None or not password_matches:
        # One message for both cases, so the response does not reveal which emails exist.
        raise ApiError(401, "invalid_credentials", "Incorrect email or password.")
    return session_json(user)


@blueprint.get("/me")
@login_required
def me():
    return {"user": user_json(g.user)}
