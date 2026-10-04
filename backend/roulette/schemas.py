"""The shapes of what the API accepts and returns.

Pydantic models declare each input's type and limits; `model_validate` either returns a
checked object or raises `ValidationError`, which `errors.py` turns into a 422 response.
"""

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, EmailStr, Field, field_validator

from .hours import open_state
from .models import CATEGORIES, DIETS, Restaurant, User
from .search import (
    DEFAULT_LIMIT,
    DEFAULT_RADIUS_M,
    MAX_LIMIT,
    MAX_RADIUS_M,
    MAX_SPIN_COUNT,
    Search,
)

MAX_LIST_ITEMS = 20
MAX_SEEN = 500

# Built from the same tuples the database constraint and the import use, so the accepted
# values cannot drift apart.
Category = Literal[*CATEGORIES]
Diet = Literal[*DIETS]


def split_commas(value):
    """Turn a query-string value such as "vegan, halal" into ["vegan", "halal"]."""
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return value


# A query parameter holding several values separated by commas.
CommaSeparated = BeforeValidator(split_commas)


class SearchParams(BaseModel):
    """Query parameters shared by the nearby and spin endpoints."""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius: float = Field(default=DEFAULT_RADIUS_M, gt=0, le=MAX_RADIUS_M)
    category: Annotated[tuple[Category, ...], CommaSeparated] = Field((), max_length=MAX_LIST_ITEMS)
    cuisine: Annotated[tuple[str, ...], CommaSeparated] = Field((), max_length=MAX_LIST_ITEMS)
    diet: Annotated[tuple[Diet, ...], CommaSeparated] = Field((), max_length=MAX_LIST_ITEMS)
    diet_match: Literal["all", "any"] = "all"
    open_now: bool = False

    @field_validator("cuisine")
    @classmethod
    def normalise_cuisines(cls, cuisines: tuple[str, ...]) -> tuple[str, ...]:
        # Same normalisation as the import, so "Bubble Tea" finds "bubble_tea".
        return tuple(cuisine.lower().replace(" ", "_") for cuisine in cuisines)

    def to_search(self) -> Search:
        return Search(
            lat=self.lat,
            lon=self.lon,
            radius_m=self.radius,
            categories=self.category,
            cuisines=self.cuisine,
            diets=self.diet,
            diet_match=self.diet_match,
            open_now=self.open_now,
        )


class NearbyParams(SearchParams):
    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)


class SpinParams(SearchParams):
    count: int = Field(default=1, ge=1, le=MAX_SPIN_COUNT)
    # Ids shown in earlier spins; at most one of them may be picked again.
    seen: Annotated[tuple[int, ...], CommaSeparated] = Field((), max_length=MAX_SEEN)


class Credentials(BaseModel):
    """Body of the login request. Deliberately loose: login must not reveal the rules."""

    email: str = Field(max_length=254)
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, email: str) -> str:
        return email.strip().lower()


class Registration(Credentials):
    """Body of the register request: a real email address and an acceptable password."""

    email: EmailStr
    # The upper bound stops someone making the server hash megabytes of text.
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def require_a_digit(cls, password: str) -> str:
        if not re.search(r"\d", password):
            raise ValueError("Password must contain at least one number")
        return password


def restaurant_json(restaurant: Restaurant, now: datetime, distance_m: float | None = None) -> dict:
    data = {
        "id": restaurant.id,
        "name": restaurant.name,
        "category": restaurant.category,
        "lat": restaurant.lat,
        "lon": restaurant.lon,
        "cuisines": restaurant.cuisines,
        "diets": restaurant.diets,
        "opening_hours": restaurant.opening_hours,
        # true, false, or null when the hours are missing or unreadable.
        "open_now": open_state(restaurant.opening_hours, now),
        "address": restaurant.address,
        "phone": restaurant.phone,
        "website": restaurant.website,
    }
    if distance_m is not None:
        data["distance_m"] = round(distance_m)
    return data


def user_json(user: User) -> dict:
    return {"id": user.id, "email": user.email}
