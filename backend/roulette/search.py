"""Finding places to eat near a point."""

from collections.abc import Collection, Iterator
from dataclasses import dataclass
from datetime import datetime
from itertools import islice
from typing import Literal

from sqlalchemy import Select, func, select

from .extensions import db
from .hours import is_open, local_now
from .models import Restaurant, point

DEFAULT_RADIUS_M = 2_000
MAX_RADIUS_M = 25_000
DEFAULT_LIMIT = 50
MAX_LIMIT = 200
MAX_SPIN_COUNT = 5


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


def stream(search: Search, query: Select, now: datetime | None) -> Iterator[Match]:
    """Yield the rows of `query` in order, skipping closed places if "open now" was asked for.

    Rows are fetched in chunks and only as far as the caller reads, so a caller that stops
    after a few matches never loads the rest.
    """
    now = now or local_now()
    for restaurant, distance_m in db.session.execute(query).yield_per(200):
        if not search.open_now or is_open(restaurant.opening_hours, now):
            yield Match(restaurant, distance_m)


def nearby(search: Search, limit: int = DEFAULT_LIMIT, now: datetime | None = None) -> list[Match]:
    """Return the closest places that satisfy `search`, nearest first."""
    query = matching(search).order_by("distance_m", Restaurant.id)
    if not search.open_now:
        # Without "open now" every row counts, so the database can apply the limit.
        # With it, an unknown number of rows will turn out closed, so `islice` stops
        # reading the stream once enough open ones have been found.
        query = query.limit(limit)
    return list(islice(stream(search, query, now), limit))


def spin(
    search: Search,
    count: int = 1,
    seen_ids: Collection[int] = (),
    now: datetime | None = None,
) -> list[Match]:
    """Return up to `count` different places chosen at random from those that satisfy `search`.

    At most one of them is a place in `seen_ids` (ones shown in earlier spins), so every
    spin is mostly new. Fewer than `count` are returned when there are not enough places.
    """
    seen_ids = set(seen_ids)
    query = matching(search).order_by(func.random())
    if not search.open_now and not seen_ids:
        query = query.limit(count)

    picks = []
    seen_used = False
    # The rows arrive in random order, so taking them first come, first served is a fair
    # random choice; a second already-seen place is simply skipped.
    for match in stream(search, query, now):
        if match.restaurant.id in seen_ids:
            if seen_used:
                continue
            seen_used = True
        picks.append(match)
        if len(picks) == count:
            break
    return picks
