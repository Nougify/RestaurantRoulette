"""Password hashing, login tokens, and the decorator that protects routes."""

from datetime import UTC, datetime
from functools import wraps

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from flask import current_app, g, request

from .errors import ApiError
from .extensions import db
from .models import User

TOKEN_ALGORITHM = "HS256"

# Argon2id with the library's recommended cost settings. The salt is generated per
# password and stored inside the hash string, so no separate salt column is needed.
hasher = PasswordHasher()

# Verified when the email is unknown, so that login takes the same time whether or not
# an account exists and response timing cannot be used to discover registered emails.
DUMMY_HASH = hasher.hash("no account has this password")


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_token(user: User) -> str:
    """Return a signed JWT saying who the bearer is and when the token stops being valid."""
    now = datetime.now(UTC)
    claims = {"sub": str(user.id), "iat": now, "exp": now + current_app.config["TOKEN_LIFETIME"]}
    return jwt.encode(claims, current_app.config["SECRET_KEY"], algorithm=TOKEN_ALGORITHM)


def user_from_token(token: str) -> User | None:
    """Return the user a token belongs to, or None if it is forged, expired or orphaned."""
    try:
        # `algorithms` is an allow-list: a token claiming any other algorithm is rejected.
        claims = jwt.decode(
            token,
            current_app.config["SECRET_KEY"],
            algorithms=[TOKEN_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        user_id = int(claims["sub"])
    except (jwt.InvalidTokenError, ValueError):
        return None
    return db.session.get(User, user_id)


def login_required(view):
    """Reject the request with 401 unless it carries a valid `Authorization: Bearer` token.

    The signed-in user is made available to the view as `g.user`.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        user = user_from_token(token.strip()) if scheme.lower() == "bearer" else None
        if user is None:
            raise ApiError(401, "unauthorized", "Sign in to do this.")
        g.user = user
        return view(*args, **kwargs)

    return wrapped
