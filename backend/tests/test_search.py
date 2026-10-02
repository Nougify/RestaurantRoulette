from collections import Counter
from datetime import datetime

import pytest

from roulette.extensions import db
from roulette.models import Restaurant, point
from roulette.search import Search, nearby, pick_random

# The search origin, and points at known distances north of it.
# One degree of latitude is about 111.2 km, so 0.001 degrees is about 111 m.
ORIGIN = (49.2800, -123.1200)
FRIDAY_EVENING = datetime(2026, 10, 2, 19, 30)


def north(metres):
    return (ORIGIN[0] + metres / 111_200, ORIGIN[1])


def add(name, metres=100, **fields):
    """Store a restaurant `metres` north of ORIGIN."""
    restaurant = Restaurant(
        osm_type="node",
        osm_id=abs(hash(name)) % 10**9,
        name=name,
        category=fields.pop("category", "restaurant"),
        location=point(*north(metres)),
        **fields,
    )
    db.session.add(restaurant)
    db.session.commit()
    return restaurant


def search(**fields):
    return Search(lat=ORIGIN[0], lon=ORIGIN[1], **fields)


def names(matches):
    return [match.restaurant.name for match in matches]


def test_nearby_returns_places_inside_the_radius_nearest_first():
    add("far", 1500)
    add("near", 200)
    add("outside", 2500)

    matches = nearby(search())

    assert names(matches) == ["near", "far"]
    assert matches[0].distance_m == pytest.approx(200, abs=2)
    assert matches[1].distance_m == pytest.approx(1500, abs=5)


def test_radius_is_adjustable():
    add("near", 200)
    add("far", 1500)

    assert names(nearby(search(radius_m=500))) == ["near"]
    assert names(nearby(search(radius_m=3000))) == ["near", "far"]


def test_limit_keeps_the_closest():
    for metres in (300, 100, 200):
        add(f"at {metres}", metres)

    assert names(nearby(search(), limit=2)) == ["at 100", "at 200"]


def test_category_filter():
    add("diner", category="restaurant")
    add("espresso", category="cafe")
    add("burgers", category="fast_food")

    assert sorted(names(nearby(search(categories=("cafe", "fast_food"))))) == [
        "burgers",
        "espresso",
    ]


def test_cuisine_filter_matches_any_listed_cuisine():
    add("pizzeria", cuisines=["pizza", "italian"])
    add("sushi bar", cuisines=["sushi"])
    add("untagged")

    assert names(nearby(search(cuisines=("italian",)))) == ["pizzeria"]
    assert sorted(names(nearby(search(cuisines=("sushi", "pizza"))))) == ["pizzeria", "sushi bar"]


def test_diet_filter_all_versus_any():
    add("both", diets=["vegan", "halal"])
    add("vegan only", diets=["vegan"])
    add("halal only", diets=["halal"])
    add("untagged")
    wanted = ("vegan", "halal")

    assert names(nearby(search(diets=wanted))) == ["both"]
    assert names(nearby(search(diets=wanted, diet_match="all"))) == ["both"]
    assert sorted(names(nearby(search(diets=wanted, diet_match="any")))) == [
        "both",
        "halal only",
        "vegan only",
    ]


def test_filters_combine():
    add("match", category="cafe", cuisines=["coffee_shop"], diets=["vegan"])
    add("wrong diet", category="cafe", cuisines=["coffee_shop"])
    add("wrong category", category="restaurant", cuisines=["coffee_shop"], diets=["vegan"])
    add("too far", 5000, category="cafe", cuisines=["coffee_shop"], diets=["vegan"])

    found = nearby(search(categories=("cafe",), cuisines=("coffee_shop",), diets=("vegan",)))

    assert names(found) == ["match"]


def test_open_now_keeps_only_places_known_to_be_open():
    add("open", opening_hours="Mo-Su 11:00-22:00")
    add("closed", opening_hours="Mo-Su 07:00-15:00")
    add("unknown")
    add("unreadable", opening_hours="ask inside")

    assert names(nearby(search(open_now=True), now=FRIDAY_EVENING)) == ["open"]
    assert len(nearby(search(), now=FRIDAY_EVENING)) == 4


def test_open_now_limit_counts_open_places_only():
    add("closed nearest", 100, opening_hours="Mo-Su 07:00-15:00")
    add("open A", 200, opening_hours="Mo-Su 11:00-22:00")
    add("open B", 300, opening_hours="24/7")
    add("open C", 400, opening_hours="24/7")

    assert names(nearby(search(open_now=True), limit=2, now=FRIDAY_EVENING)) == ["open A", "open B"]


def test_pick_random_returns_none_when_nothing_matches():
    add("outside", 5000)

    assert pick_random(search()) is None


def test_pick_random_respects_filters_and_reports_distance():
    add("vegan", 300, diets=["vegan"])
    add("other", 100)

    for _ in range(10):
        match = pick_random(search(diets=("vegan",)))
        assert match.restaurant.name == "vegan"
        assert match.distance_m == pytest.approx(300, abs=2)


def test_pick_random_only_picks_open_places_when_asked():
    add("open", opening_hours="Mo-Su 11:00-22:00")
    add("closed", opening_hours="Mo-Su 07:00-15:00")
    add("unknown")

    picks = {
        pick_random(search(open_now=True), now=FRIDAY_EVENING).restaurant.name for _ in range(15)
    }

    assert picks == {"open"}


def test_pick_random_reaches_every_match():
    for name in ("a", "b", "c"):
        add(name)

    picks = Counter(pick_random(search()).restaurant.name for _ in range(60))

    # Each has a 1-in-3 chance per draw; missing one in 60 draws is a ~1e-10 event.
    assert set(picks) == {"a", "b", "c"}
