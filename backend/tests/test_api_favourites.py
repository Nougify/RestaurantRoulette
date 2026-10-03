import pytest
from sqlalchemy import func, select

from roulette.extensions import db
from roulette.models import Favourite, Restaurant, point


def add_restaurant(osm_id, name):
    restaurant = Restaurant(
        osm_type="node",
        osm_id=osm_id,
        name=name,
        category="restaurant",
        location=point(49.28, -123.12),
    )
    db.session.add(restaurant)
    db.session.commit()
    return restaurant.id


def favourite_names(client, headers):
    response = client.get("/api/favourites", headers=headers)
    assert response.status_code == 200
    return [restaurant["name"] for restaurant in response.json["restaurants"]]


def other_user(client):
    response = client.post(
        "/api/auth/register", json={"email": "other@example.com", "password": "another1user"}
    )
    return {"Authorization": f"Bearer {response.json['token']}"}


@pytest.mark.parametrize(
    "method, url",
    [("get", "/api/favourites"), ("put", "/api/favourites/1"), ("delete", "/api/favourites/1")],
)
def test_favourites_require_signing_in(client, method, url):
    assert getattr(client, method)(url).status_code == 401


def test_new_user_has_no_favourites(client, auth):
    assert favourite_names(client, auth) == []


def test_saved_restaurants_are_listed_newest_first_with_details(client, auth):
    first = add_restaurant(1, "first saved")
    second = add_restaurant(2, "second saved")

    assert client.put(f"/api/favourites/{first}", headers=auth).status_code == 204
    assert client.put(f"/api/favourites/{second}", headers=auth).status_code == 204

    response = client.get("/api/favourites", headers=auth)
    assert [r["name"] for r in response.json["restaurants"]] == ["second saved", "first saved"]
    newest = response.json["restaurants"][0]
    assert newest["id"] == second
    assert (newest["lat"], newest["lon"]) == pytest.approx((49.28, -123.12))
    assert "distance_m" not in newest


def test_saving_twice_keeps_one_favourite(client, auth):
    restaurant_id = add_restaurant(1, "regular")

    statuses = [
        client.put(f"/api/favourites/{restaurant_id}", headers=auth).status_code for _ in range(2)
    ]

    assert statuses == [204, 204]
    assert db.session.scalar(select(func.count()).select_from(Favourite)) == 1


def test_saving_an_unknown_restaurant_is_a_404(client, auth):
    response = client.put("/api/favourites/12345", headers=auth)

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"


def test_removing_a_favourite(client, auth):
    kept = add_restaurant(1, "kept")
    removed = add_restaurant(2, "removed")
    client.put(f"/api/favourites/{kept}", headers=auth)
    client.put(f"/api/favourites/{removed}", headers=auth)

    assert client.delete(f"/api/favourites/{removed}", headers=auth).status_code == 204
    assert favourite_names(client, auth) == ["kept"]
    # Removing again, or removing something never saved, still succeeds.
    assert client.delete(f"/api/favourites/{removed}", headers=auth).status_code == 204


def test_users_only_see_and_change_their_own_favourites(client, auth):
    restaurant_id = add_restaurant(1, "mine")
    client.put(f"/api/favourites/{restaurant_id}", headers=auth)
    stranger = other_user(client)

    assert favourite_names(client, stranger) == []
    client.delete(f"/api/favourites/{restaurant_id}", headers=stranger)
    assert favourite_names(client, auth) == ["mine"]
