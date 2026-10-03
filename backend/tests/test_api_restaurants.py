from datetime import datetime

import pytest

from roulette.api import restaurants as restaurants_api
from roulette.extensions import db
from roulette.hours import LOCAL_TIMEZONE
from roulette.models import Restaurant, point

ORIGIN = {"lat": 49.2800, "lon": -123.1200}
FRIDAY_EVENING = datetime(2026, 10, 2, 19, 30, tzinfo=LOCAL_TIMEZONE)


@pytest.fixture(autouse=True)
def friday_evening(monkeypatch):
    """Freeze the API's clock so opening-hours results do not depend on when tests run."""
    monkeypatch.setattr(restaurants_api, "local_now", lambda: FRIDAY_EVENING)


def add(osm_id, name, metres=100, **fields):
    """Store a restaurant `metres` north of ORIGIN and return its id."""
    restaurant = Restaurant(
        osm_type="node",
        osm_id=osm_id,
        name=name,
        category=fields.pop("category", "restaurant"),
        location=point(ORIGIN["lat"] + metres / 111_200, ORIGIN["lon"]),
        **fields,
    )
    db.session.add(restaurant)
    db.session.commit()
    return restaurant.id


def names(response):
    return [restaurant["name"] for restaurant in response.json["restaurants"]]


def test_health(client):
    response = client.get("/api/health")
    assert (response.status_code, response.json) == (200, {"status": "ok"})


def test_nearby_returns_full_restaurant_details(client):
    restaurant_id = add(
        1,
        "Test Kitchen",
        200,
        cuisines=["pizza"],
        diets=["vegan"],
        opening_hours="Mo-Su 11:00-22:00",
        address="1 Main Street, Vancouver",
        phone="+1 604 555 0100",
        website="https://example.com",
    )

    response = client.get("/api/restaurants/nearby", query_string=ORIGIN)

    assert response.status_code == 200
    (restaurant,) = response.json["restaurants"]
    assert restaurant.pop("lat") == pytest.approx(ORIGIN["lat"] + 200 / 111_200)
    assert restaurant.pop("lon") == pytest.approx(ORIGIN["lon"])
    assert restaurant.pop("distance_m") in (199, 200, 201)
    assert restaurant == {
        "id": restaurant_id,
        "name": "Test Kitchen",
        "category": "restaurant",
        "cuisines": ["pizza"],
        "diets": ["vegan"],
        "opening_hours": "Mo-Su 11:00-22:00",
        "open_now": True,
        "address": "1 Main Street, Vancouver",
        "phone": "+1 604 555 0100",
        "website": "https://example.com",
    }


def test_nearby_defaults_to_two_km_nearest_first(client):
    add(1, "far", 1500)
    add(2, "near", 200)
    add(3, "outside", 2500)

    assert names(client.get("/api/restaurants/nearby", query_string=ORIGIN)) == ["near", "far"]


def test_nearby_applies_every_filter(client):
    add(1, "match", category="cafe", cuisines=["bubble_tea"], diets=["vegan", "halal"])
    add(2, "wrong category", cuisines=["bubble_tea"], diets=["vegan", "halal"])
    add(3, "wrong cuisine", category="cafe", cuisines=["pizza"], diets=["vegan", "halal"])
    add(4, "one diet", category="cafe", cuisines=["bubble_tea"], diets=["vegan"])
    add(5, "too far", 900, category="cafe", cuisines=["bubble_tea"], diets=["vegan", "halal"])

    query = ORIGIN | {
        "radius": 500,
        "category": "cafe,fast_food",
        "cuisine": "Bubble Tea, ramen",
        "diet": "vegan,halal",
    }

    assert names(client.get("/api/restaurants/nearby", query_string=query)) == ["match"]
    any_diet = query | {"diet_match": "any"}
    assert sorted(names(client.get("/api/restaurants/nearby", query_string=any_diet))) == [
        "match",
        "one diet",
    ]


def test_open_now_filter_and_three_way_open_state(client):
    add(1, "open", 100, opening_hours="Mo-Su 11:00-22:00")
    add(2, "closed", 200, opening_hours="Mo-Su 07:00-15:00")
    add(3, "unknown", 300)

    everything = client.get("/api/restaurants/nearby", query_string=ORIGIN).json["restaurants"]
    assert [r["open_now"] for r in everything] == [True, False, None]

    only_open = client.get("/api/restaurants/nearby", query_string=ORIGIN | {"open_now": "true"})
    assert names(only_open) == ["open"]


def test_nearby_limit(client):
    for osm_id, metres in enumerate((300, 100, 200), start=1):
        add(osm_id, f"at {metres}", metres)

    response = client.get("/api/restaurants/nearby", query_string=ORIGIN | {"limit": 2})

    assert names(response) == ["at 100", "at 200"]


def test_random_returns_one_matching_restaurant(client):
    add(1, "vegan", 300, diets=["vegan"])
    add(2, "other", 100)

    response = client.get("/api/restaurants/random", query_string=ORIGIN | {"diet": "vegan"})

    assert response.status_code == 200
    assert response.json["restaurant"]["name"] == "vegan"
    assert response.json["restaurant"]["distance_m"] in (299, 300, 301)


def test_random_returns_null_when_nothing_matches(client):
    add(1, "outside", 5000)

    response = client.get("/api/restaurants/random", query_string=ORIGIN)

    assert (response.status_code, response.json) == (200, {"restaurant": None})


def test_random_never_returns_an_excluded_restaurant(client):
    seen = [add(1, "seen A"), add(2, "seen B")]
    add(3, "fresh")
    query = ORIGIN | {"exclude": ",".join(str(id_) for id_ in seen)}

    picks = {
        client.get("/api/restaurants/random", query_string=query).json["restaurant"]["name"]
        for _ in range(10)
    }
    assert picks == {"fresh"}

    everything_seen = ORIGIN | {"exclude": "1,2,3"}
    response = client.get("/api/restaurants/random", query_string=everything_seen)
    assert response.json == {"restaurant": None}


@pytest.mark.parametrize(
    "query, field",
    [
        ({"lon": -123.12}, "lat"),
        ({"lat": 49.28}, "lon"),
        (ORIGIN | {"lat": 91}, "lat"),
        (ORIGIN | {"lon": "west"}, "lon"),
        (ORIGIN | {"lat": "nan"}, "lat"),
        (ORIGIN | {"radius": 0}, "radius"),
        (ORIGIN | {"radius": 25001}, "radius"),
        (ORIGIN | {"category": "pub"}, "category.0"),
        (ORIGIN | {"diet": "vegan,paleo"}, "diet.1"),
        (ORIGIN | {"diet_match": "some"}, "diet_match"),
        (ORIGIN | {"open_now": "perhaps"}, "open_now"),
        (ORIGIN | {"limit": 0}, "limit"),
        (ORIGIN | {"limit": 201}, "limit"),
    ],
)
def test_nearby_rejects_invalid_input(client, query, field):
    response = client.get("/api/restaurants/nearby", query_string=query)

    assert response.status_code == 422
    error = response.json["error"]
    assert error["code"] == "validation_error"
    assert [detail["field"] for detail in error["details"]] == [field]


def test_random_rejects_invalid_exclude(client):
    response = client.get("/api/restaurants/random", query_string=ORIGIN | {"exclude": "1,two"})

    assert response.status_code == 422
    assert response.json["error"]["details"][0]["field"] == "exclude.1"


def test_radius_at_the_cap_is_accepted(client):
    add(1, "distant", 24_000)

    response = client.get("/api/restaurants/nearby", query_string=ORIGIN | {"radius": 25000})

    assert names(response) == ["distant"]


def test_filters_lists_choices_with_most_common_cuisines_first(client):
    add(1, "a", cuisines=["pizza", "italian"])
    add(2, "b", cuisines=["pizza"])
    add(3, "c")

    response = client.get("/api/filters")

    assert response.json == {
        "categories": ["restaurant", "cafe", "fast_food"],
        "diets": ["vegetarian", "vegan", "halal", "kosher", "gluten_free"],
        "cuisines": [{"name": "pizza", "count": 2}, {"name": "italian", "count": 1}],
        "radius": {"default": 2000, "max": 25000},
    }


def test_unknown_url_is_a_json_404(client):
    response = client.get("/api/nowhere")

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"


def test_wrong_method_is_a_json_405(client):
    response = client.post("/api/restaurants/nearby")

    assert response.status_code == 405
    assert response.json["error"]["code"] == "method_not_allowed"


def test_unexpected_error_is_a_json_500_without_internals(app, client, monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("database password is hunter2")

    monkeypatch.setattr(restaurants_api, "nearby", explode)
    # In testing mode Flask re-raises errors for the test to see; turn that off to
    # exercise what a real client would receive.
    monkeypatch.setitem(app.config, "PROPAGATE_EXCEPTIONS", False)

    response = client.get("/api/restaurants/nearby", query_string=ORIGIN)

    assert response.status_code == 500
    assert response.json["error"]["code"] == "internal_error"
    assert "hunter2" not in response.get_data(as_text=True)


def test_cors_allows_the_frontend_origin_only(client):
    allowed = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    other = client.get("/api/health", headers={"Origin": "https://evil.example"})

    assert allowed.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "Access-Control-Allow-Origin" not in other.headers
