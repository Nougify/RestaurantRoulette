"""The signed-in user's saved restaurants."""

from flask import Blueprint, g
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from ..errors import ApiError
from ..extensions import db
from ..hours import local_now
from ..models import Favourite, Restaurant
from ..schemas import restaurant_json
from ..security import login_required

blueprint = Blueprint("favourites", __name__, url_prefix="/favourites")


@blueprint.get("")
@login_required
def list_favourites():
    """Return the user's favourites, most recently saved first."""
    restaurants = db.session.scalars(
        select(Restaurant)
        .join(Favourite, Favourite.restaurant_id == Restaurant.id)
        .where(Favourite.user_id == g.user.id)
        .order_by(Favourite.created_at.desc(), Restaurant.id)
    )
    now = local_now()
    return {"restaurants": [restaurant_json(restaurant, now) for restaurant in restaurants]}


@blueprint.put("/<int:restaurant_id>")
@login_required
def add_favourite(restaurant_id: int):
    """Save a restaurant. PUT because repeating it leaves the same result (idempotent)."""
    if db.session.get(Restaurant, restaurant_id) is None:
        raise ApiError(404, "not_found", "There is no restaurant with this id.")
    db.session.execute(
        insert(Favourite)
        .values(user_id=g.user.id, restaurant_id=restaurant_id)
        .on_conflict_do_nothing()
    )
    db.session.commit()
    return "", 204


@blueprint.delete("/<int:restaurant_id>")
@login_required
def remove_favourite(restaurant_id: int):
    """Unsave a restaurant. Succeeds even if it was not saved, so retries are harmless."""
    # The user id comes from the token, never from the request, so one user cannot
    # touch another's favourites.
    db.session.execute(
        delete(Favourite).where(
            Favourite.user_id == g.user.id, Favourite.restaurant_id == restaurant_id
        )
    )
    db.session.commit()
    return "", 204
