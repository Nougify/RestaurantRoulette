"""Finding places to eat near a point."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import Select, func, select

from .extensions import db
from .hours import is_open, local_now
from .models import Restaurant, point

DEFAULT_RADIUS_M = 2_000
MAX_RADIUS_M = 25_000
DEFAULT_LIMIT = 50
MAX_LIMIT = 200


@dataclass(frozen=True)
class Search:
    """What the visitor is looking for. An empty filter means "no restriction"."""

    lat: float
    lon: float
    radius_m: float = DEFAULT_RADIUS_M
    categories: tuple[str, ...] = ()
    # A place matches if it serves any one of these cuisines.
    cuisines: tuple[str, ...] = ()
    diets: tuple[str, ...] = ()
    # "all": the place must cater for every listed diet. "any": at least one of them.
    diet_match: Literal["all", "any"] = "all"
    open_now: bool = False


@dataclass(frozen=True)
class Match:
    restaurant: Restaurant
    distance_m: float


def matching(search: Search) -> Select:
    """Return the query for every place that satisfies `search`, with its distance in metres.

    Everything except "open now" is filtered here, inside the database, where indexes apply.
    """
    origin = point(search.lat, search.lon)
    query = select(
        Restaurant, func.ST_Distance(Restaurant.location, origin).label("distance_m")
    ).where(func.ST_DWithin(Restaurant.location, origin, search.radius_m))

    if search.categories:
        query = query.where(Restaurant.category.in_(search.categories))
    if search.cuisines:
        # `&&`: the two arrays have at least one element in common.
        query = query.where(Restaurant.cuisines.overlap(list(search.cuisines)))
    if search.diets:
        diets = list(search.diets)
        # `@>`: the column's array contains every element of `diets`.
        condition = (
            Restaurant.diets.contains(diets)
            if search.diet_match == "all"
            else Restaurant.diets.overlap(diets)
        )
        query = query.where(condition)
    if search.open_now:
        # Opening hours are evaluated in Python, but places with none recorded can never
        # count as open, so they are dropped here rather than fetched.
        query = query.where(Restaurant.opening_hours.is_not(None))
    return query


def run(search: Search, query: Select, limit: int, now: datetime | None) -> list[Match]:
    """Run `query` and return up to `limit` matches, applying "open now" if asked for."""
    if not search.open_now:
        rows = db.session.execute(query.limit(limit))
        return [Match(restaurant, distance_m) for restaurant, distance_m in rows]

    now = now or local_now()
    matches = []
    # The limit cannot be applied in SQL, because an unknown number of rows will turn
    # out to be closed. Rows are streamed in order and reading stops once enough are open.
    for restaurant, distance_m in db.session.execute(query).yield_per(200):
        if is_open(restaurant.opening_hours, now):
            matches.append(Match(restaurant, distance_m))
            if len(matches) == limit:
                break
    return matches


def nearby(search: Search, limit: int = DEFAULT_LIMIT, now: datetime | None = None) -> list[Match]:
    """Return the closest places that satisfy `search`, nearest first."""
    return run(search, matching(search).order_by("distance_m", Restaurant.id), limit, now)


def pick_random(search: Search, now: datetime | None = None) -> Match | None:
    """Return one place chosen at random from those that satisfy `search`, or None."""
    matches = run(search, matching(search).order_by(func.random()), 1, now)
    return matches[0] if matches else None
