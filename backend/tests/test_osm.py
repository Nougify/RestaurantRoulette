import pytest
import requests

from roulette import osm
from roulette.osm import (
    OverpassError,
    build_query,
    fetch_elements,
    parse_address,
    parse_cuisines,
    parse_diets,
    parse_element,
    parse_website,
)


def node(**tags):
    tags = {"name": "Test Kitchen", "amenity": "restaurant"} | tags
    return {"type": "node", "id": 1, "lat": 49.28, "lon": -123.12, "tags": tags}


def test_query_asks_for_each_category_inside_the_area():
    query = build_query(area_id=3600000042)
    assert "area(id:3600000042)" in query
    assert "^(restaurant|cafe|fast_food)$" in query
    assert "out tags center;" in query


def test_node_becomes_a_row():
    row = parse_element(
        node(
            cuisine="pizza;italian",
            opening_hours=" Mo-Su 11:00-22:00 ",
            phone="+1 604 555 0100",
            **{"diet:vegan": "yes"},
        )
    )
    assert row["osm_type"] == "node"
    assert row["osm_id"] == 1
    assert row["name"] == "Test Kitchen"
    assert row["category"] == "restaurant"
    assert row["location"].desc == "POINT(-123.12 49.28)"
    assert row["cuisines"] == ["pizza", "italian"]
    assert row["diets"] == ["vegan"]
    assert row["opening_hours"] == "Mo-Su 11:00-22:00"
    assert row["phone"] == "+1 604 555 0100"


def test_way_uses_its_center_point():
    way = {
        "type": "way",
        "id": 9,
        "center": {"lat": 49.2, "lon": -123.0},
        "tags": {"name": "Big Diner", "amenity": "fast_food"},
    }
    assert parse_element(way)["location"].desc == "POINT(-123.0 49.2)"


@pytest.mark.parametrize(
    "element",
    [
        node(name="   "),
        {"type": "node", "id": 1, "lat": 49.28, "lon": -123.12, "tags": {"amenity": "cafe"}},
        node(amenity="pub"),
        {"type": "way", "id": 2, "tags": {"name": "No Position", "amenity": "cafe"}},
    ],
    ids=["blank name", "no name", "unwanted category", "no coordinates"],
)
def test_unusable_elements_are_skipped(element):
    assert parse_element(element) is None


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, []),
        ("sushi", ["sushi"]),
        ("Pizza; italian ;", ["pizza", "italian"]),
        ("ice cream;ice_cream", ["ice_cream"]),
    ],
)
def test_parse_cuisines(value, expected):
    assert parse_cuisines(value) == expected


def test_only_explicit_yes_or_only_counts_as_a_diet():
    tags = {
        "diet:vegetarian": "only",
        "diet:vegan": "yes",
        "diet:halal": "no",
        "diet:kosher": "limited",
    }
    assert parse_diets(tags) == ["vegetarian", "vegan"]


@pytest.mark.parametrize(
    "tags, expected",
    [
        ({}, None),
        ({"addr:housenumber": "123", "addr:street": "Main Street"}, "123 Main Street"),
        (
            {"addr:housenumber": "123", "addr:street": "Main Street", "addr:city": "Burnaby"},
            "123 Main Street, Burnaby",
        ),
        ({"addr:city": "Surrey"}, "Surrey"),
    ],
)
def test_parse_address(tags, expected):
    assert parse_address(tags) == expected


@pytest.mark.parametrize(
    "tags, expected",
    [
        ({}, None),
        ({"website": "https://example.com/menu"}, "https://example.com/menu"),
        ({"website": "example.com"}, "https://example.com"),
        ({"contact:website": "http://example.com"}, "http://example.com"),
        ({"website": "javascript:alert(1)"}, None),
        ({"website": "ftp://example.com"}, None),
    ],
)
def test_parse_website(tags, expected):
    assert parse_website(tags) == expected


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.ok = status_code < 400
        self._payload = payload

    def json(self):
        return self._payload


def fake_post(monkeypatch, *outcomes):
    """Make `requests.post` return (or raise) each of `outcomes` in turn; return the calls."""
    remaining = list(outcomes)
    calls = []

    def post(url, **kwargs):
        calls.append(url)
        outcome = remaining.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(osm.requests, "post", post)
    return calls


def test_fetch_returns_elements(monkeypatch):
    fake_post(monkeypatch, FakeResponse(200, {"elements": [{"id": 1}]}))
    assert fetch_elements("query") == [{"id": 1}]


def test_fetch_retries_on_another_server_when_busy(monkeypatch):
    calls = fake_post(
        monkeypatch,
        FakeResponse(429),
        requests.ConnectionError("down"),
        FakeResponse(200, {"elements": []}),
    )
    assert fetch_elements("query", wait_seconds=0) == []
    assert calls == [osm.OVERPASS_URLS[0], osm.OVERPASS_URLS[1], osm.OVERPASS_URLS[0]]


def test_fetch_gives_up_after_the_last_attempt(monkeypatch):
    calls = fake_post(monkeypatch, FakeResponse(504), FakeResponse(504))
    with pytest.raises(OverpassError, match="gave up after 2 attempts"):
        fetch_elements("query", attempts=2, wait_seconds=0)
    assert len(calls) == 2


def test_fetch_does_not_retry_a_rejected_query(monkeypatch):
    calls = fake_post(monkeypatch, FakeResponse(400))
    with pytest.raises(OverpassError, match="HTTP 400"):
        fetch_elements("query", wait_seconds=0)
    assert len(calls) == 1


def test_fetch_rejects_a_partial_result(monkeypatch):
    fake_post(monkeypatch, FakeResponse(200, {"elements": [], "remark": "runtime error: timeout"}))
    with pytest.raises(OverpassError, match="timeout"):
        fetch_elements("query")
