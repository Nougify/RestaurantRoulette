from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from roulette import create_app
from roulette.config import TestConfig
from roulette.extensions import db, limiter
from roulette.models import User

EMAIL = "diner@example.com"
PASSWORD = "hungry4food"
CREDENTIALS = {"email": EMAIL, "password": PASSWORD}


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_creates_a_user_and_signs_them_in(client):
    response = client.post("/api/auth/register", json=CREDENTIALS)

    assert response.status_code == 201
    assert response.json["user"]["email"] == EMAIL
    me = client.get("/api/auth/me", headers=bearer(response.json["token"]))
    assert me.json == {"user": response.json["user"]}


def test_password_is_stored_hashed_and_never_returned(client):
    response = client.post("/api/auth/register", json=CREDENTIALS)

    stored = db.session.scalars(select(User)).one().password_hash
    assert stored.startswith("$argon2id$")
    assert PASSWORD not in stored
    assert "password" not in response.get_data(as_text=True)


def test_email_is_case_insensitive(client):
    client.post("/api/auth/register", json={"email": " Diner@Example.COM ", "password": PASSWORD})

    assert db.session.scalars(select(User.email)).one() == EMAIL
    assert client.post("/api/auth/login", json=CREDENTIALS).status_code == 200
    shouted = {"email": "DINER@EXAMPLE.COM", "password": PASSWORD}
    assert client.post("/api/auth/register", json=shouted).status_code == 409


def test_registering_an_existing_email_is_a_conflict(client):
    client.post("/api/auth/register", json=CREDENTIALS)

    response = client.post("/api/auth/register", json=CREDENTIALS)

    assert response.status_code == 409
    assert response.json["error"]["code"] == "email_taken"


@pytest.mark.parametrize(
    "body, field",
    [
        ({"email": "not-an-email", "password": PASSWORD}, "email"),
        ({"password": PASSWORD}, "email"),
        ({"email": EMAIL}, "password"),
        ({"email": EMAIL, "password": "short1"}, "password"),
        ({"email": EMAIL, "password": "nodigitshere"}, "password"),
        ({"email": EMAIL, "password": "1" * 129}, "password"),
    ],
    ids=["bad email", "no email", "no password", "too short", "no number", "too long"],
)
def test_register_rejects_invalid_input(client, body, field):
    response = client.post("/api/auth/register", json=body)

    assert response.status_code == 422
    assert [detail["field"] for detail in response.json["error"]["details"]] == [field]
    assert db.session.scalars(select(User)).all() == []


@pytest.mark.parametrize("kwargs", [{"data": "not json"}, {"json": ["a", "list"]}, {}])
def test_body_must_be_a_json_object(client, kwargs):
    response = client.post("/api/auth/register", **kwargs)

    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_json"


def test_login_returns_a_working_token(client):
    client.post("/api/auth/register", json=CREDENTIALS)

    response = client.post("/api/auth/login", json=CREDENTIALS)

    assert response.status_code == 200
    me = client.get("/api/auth/me", headers=bearer(response.json["token"]))
    assert me.json["user"]["email"] == EMAIL


def test_wrong_password_and_unknown_email_get_the_same_answer(client):
    client.post("/api/auth/register", json=CREDENTIALS)

    wrong_password = client.post("/api/auth/login", json={"email": EMAIL, "password": "wrong1234"})
    unknown_email = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json == unknown_email.json
    assert wrong_password.json["error"]["code"] == "invalid_credentials"


def token_for(app, user_id, secret=None, lifetime=timedelta(hours=1), **extra):
    claims = {"sub": str(user_id), "exp": datetime.now(UTC) + lifetime, **extra}
    return jwt.encode(claims, secret or app.config["SECRET_KEY"], algorithm="HS256")


def test_token_lasts_seven_days(app, client):
    token = client.post("/api/auth/register", json=CREDENTIALS).json["token"]

    claims = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])

    assert claims["exp"] - claims["iat"] == timedelta(days=7).total_seconds()


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer not.a.token"},
        {"Authorization": "Basic ZGluZXI6aHVuZ3J5"},
    ],
    ids=["no header", "no token", "garbage token", "wrong scheme"],
)
def test_me_requires_a_valid_token(client, headers):
    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.json["error"]["code"] == "unauthorized"


def test_expired_forged_and_orphaned_tokens_are_rejected(app, client):
    user_id = client.post("/api/auth/register", json=CREDENTIALS).json["user"]["id"]
    tokens = {
        "valid": token_for(app, user_id),
        "expired": token_for(app, user_id, lifetime=timedelta(seconds=-1)),
        "forged": token_for(app, user_id, secret="a-different-secret-key-of-enough-length"),
        "unsigned": jwt.encode({"sub": str(user_id)}, None, algorithm="none"),
        "deleted user": token_for(app, user_id + 999),
    }

    statuses = {
        name: client.get("/api/auth/me", headers=bearer(token)).status_code
        for name, token in tokens.items()
    }

    assert statuses == {
        "valid": 200,
        "expired": 401,
        "forged": 401,
        "unsigned": 401,
        "deleted user": 401,
    }


class RateLimitedConfig(TestConfig):
    RATELIMIT_ENABLED = True
    AUTH_RATE_LIMIT = "3 per minute"


def test_login_is_rate_limited(monkeypatch):
    # The limiter object is shared by every app, so put its on/off switch back afterwards.
    monkeypatch.setattr(limiter, "enabled", limiter.enabled)
    client = create_app(RateLimitedConfig).test_client()

    statuses = [client.post("/api/auth/login", json=CREDENTIALS).status_code for _ in range(4)]

    assert statuses == [401, 401, 401, 429]
    assert client.get("/api/health").status_code == 200
