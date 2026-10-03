"""Public endpoints: search, the random pick, and what the filters can be set to."""

from flask import Blueprint, request
from sqlalchemy import func, select

from ..extensions import db
from ..hours import local_now
from ..models import CATEGORIES, DIETS, Restaurant
from ..schemas import NearbyParams, RandomParams, restaurant_json
from ..search import DEFAULT_RADIUS_M, MAX_RADIUS_M, nearby, pick_random

blueprint = Blueprint("restaurants", __name__)

# How many of the most common cuisines to offer as filter choices.
TOP_CUISINES = 40


@blueprint.get("/health")
def health():
    """Report that the server is up and can reach the database (for the host's health check)."""
    db.session.execute(select(1))
    return {"status": "ok"}


@blueprint.get("/restaurants/nearby")
def nearby_restaurants():
    params = NearbyParams.model_validate(request.args.to_dict())
    now = local_now()
    matches = nearby(params.to_search(), limit=params.limit, now=now)
    return {
        "restaurants": [
            restaurant_json(match.restaurant, now, match.distance_m) for match in matches
        ]
    }


@blueprint.get("/restaurants/random")
def random_restaurant():
    """Return one random match, or `null` when nothing satisfies the filters.

    An empty result is an ordinary answer to the question, not an error, so it is a 200.
    """
    params = RandomParams.model_validate(request.args.to_dict())
    now = local_now()
    match = pick_random(params.to_search(exclude_ids=params.exclude), now=now)
    return {
        "restaurant": restaurant_json(match.restaurant, now, match.distance_m) if match else None
    }


@blueprint.get("/filters")
def filters():
    """Return the values the frontend should offer in its filter controls."""
    cuisine = func.unnest(Restaurant.cuisines).label("cuisine")
    count = func.count().label("count")
    rows = db.session.execute(
        select(cuisine, count).group_by(cuisine).order_by(count.desc(), cuisine).limit(TOP_CUISINES)
    )
    return {
        "categories": list(CATEGORIES),
        "diets": list(DIETS),
        "cuisines": [{"name": name, "count": total} for name, total in rows],
        "radius": {"default": DEFAULT_RADIUS_M, "max": MAX_RADIUS_M},
    }
