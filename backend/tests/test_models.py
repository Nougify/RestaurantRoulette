import pytest
from sqlalchemy import func, insert, select, text
from sqlalchemy.exc import IntegrityError

from roulette.extensions import db
from roulette.models import Favourite, Restaurant, User, point

# Two real spots in downtown Vancouver, about 850 m apart.
WATERFRONT = (49.2856, -123.1115)
ART_GALLERY = (49.2829, -123.1207)


def make_restaurant(osm_id=1, lat_lon=WATERFRONT, **overrides):
    fields = {
        "osm_type": "node",
        "osm_id": osm_id,
        "name": "Test Kitchen",
        "category": "restaurant",
        "location": point(*lat_lon),
    }
    return Restaurant(**(fields | overrides))


def make_user(email="a@example.com"):
    return User(email=email, password_hash="not-a-real-hash")


def test_restaurant_round_trips_with_defaults():
    db.session.add(make_restaurant())
    db.session.commit()

    saved = db.session.scalars(select(Restaurant)).one()
    assert saved.name == "Test Kitchen"
    assert saved.diets == []
    assert saved.cuisines == []
    assert saved.opening_hours is None


def test_point_takes_latitude_first_but_stores_longitude_as_x():
    db.session.add(make_restaurant())
    db.session.commit()

    x, y = db.session.execute(
        text("SELECT ST_X(location::geometry), ST_Y(location::geometry) FROM restaurants")
    ).one()
    assert (y, x) == pytest.approx(WATERFRONT)


def test_distance_is_measured_in_metres():
    db.session.add(make_restaurant())
    db.session.commit()

    metres = db.session.scalar(select(func.ST_Distance(Restaurant.location, point(*ART_GALLERY))))
    assert 600 < metres < 800


def test_same_osm_element_cannot_be_stored_twice():
    db.session.add_all([make_restaurant(osm_id=7), make_restaurant(osm_id=7)])
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_same_osm_id_is_allowed_for_a_different_element_type():
    db.session.add_all([make_restaurant(osm_id=7), make_restaurant(osm_id=7, osm_type="way")])
    db.session.commit()

    assert db.session.scalar(select(func.count()).select_from(Restaurant)) == 2


def test_unknown_category_is_rejected():
    db.session.add(make_restaurant(category="nightclub"))
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_array_containment_filters_by_diet():
    db.session.add_all(
        [
            make_restaurant(osm_id=1, diets=["vegetarian", "vegan"]),
            make_restaurant(osm_id=2, diets=["vegetarian"]),
            make_restaurant(osm_id=3),
        ]
    )
    db.session.commit()

    vegan = db.session.scalars(
        select(Restaurant.osm_id).where(Restaurant.diets.contains(["vegetarian", "vegan"]))
    ).all()
    assert vegan == [1]


def test_email_must_be_unique():
    db.session.add_all([make_user(), make_user()])
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_restaurant_cannot_be_favourited_twice_by_one_user():
    user, restaurant = make_user(), make_restaurant()
    db.session.add_all([user, restaurant])
    db.session.commit()

    db.session.add(Favourite(user_id=user.id, restaurant_id=restaurant.id))
    db.session.commit()

    with pytest.raises(IntegrityError):
        db.session.execute(insert(Favourite).values(user_id=user.id, restaurant_id=restaurant.id))


def test_deleting_a_user_or_restaurant_removes_its_favourites():
    user, other, kept, removed = (
        make_user(),
        make_user("b@example.com"),
        make_restaurant(osm_id=1),
        make_restaurant(osm_id=2),
    )
    db.session.add_all([user, other, kept, removed])
    db.session.commit()
    db.session.add_all(
        [
            Favourite(user_id=user.id, restaurant_id=kept.id),
            Favourite(user_id=other.id, restaurant_id=kept.id),
            Favourite(user_id=other.id, restaurant_id=removed.id),
        ]
    )
    db.session.commit()

    db.session.delete(user)
    db.session.delete(removed)
    db.session.commit()

    remaining = db.session.execute(select(Favourite.user_id, Favourite.restaurant_id)).all()
    assert remaining == [(other.id, kept.id)]


def test_expected_indexes_exist():
    indexes = dict(
        db.session.execute(
            text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'restaurants'")
        ).all()
    )
    assert "USING gist" in indexes["idx_restaurants_location"]
    assert "USING gin" in indexes["ix_restaurants_diets"]
    assert "USING gin" in indexes["ix_restaurants_cuisines"]
