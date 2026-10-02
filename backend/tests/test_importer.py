import pytest
from sqlalchemy import func, select

from roulette import importer
from roulette.extensions import db
from roulette.importer import import_elements
from roulette.models import Favourite, Restaurant, User
from roulette.osm import OverpassError


def element(osm_id, name="Test Kitchen", **tags):
    tags = {"name": name, "amenity": "restaurant"} | tags
    return {"type": "node", "id": osm_id, "lat": 49.28, "lon": -123.12, "tags": tags}


def count(model):
    return db.session.scalar(select(func.count()).select_from(model))


def test_import_stores_usable_elements_and_counts_the_rest():
    summary = import_elements([element(1), element(2), element(3, name="")])

    assert (summary.received, summary.skipped, summary.created, summary.updated) == (3, 1, 2, 0)
    assert count(Restaurant) == 2


def test_importing_twice_changes_nothing():
    elements = [element(1), element(2)]
    import_elements(elements)
    ids = db.session.scalars(select(Restaurant.id).order_by(Restaurant.osm_id)).all()

    summary = import_elements(elements)

    assert (summary.created, summary.updated) == (0, 2)
    assert db.session.scalars(select(Restaurant.id).order_by(Restaurant.osm_id)).all() == ids


def test_reimport_updates_changed_fields_and_keeps_favourites():
    import_elements([element(1, cuisine="pizza")])
    restaurant = db.session.scalars(select(Restaurant)).one()
    user = User(email="a@example.com", password_hash="not-a-real-hash")
    db.session.add(user)
    db.session.flush()
    db.session.add(Favourite(user_id=user.id, restaurant_id=restaurant.id))
    db.session.commit()

    import_elements([element(1, name="Renamed", cuisine="sushi", **{"diet:vegan": "yes"})])

    db.session.expire_all()
    updated = db.session.scalars(select(Restaurant)).one()
    assert (updated.name, updated.cuisines, updated.diets) == ("Renamed", ["sushi"], ["vegan"])
    assert count(Favourite) == 1


def test_element_repeated_in_one_import_is_stored_once():
    summary = import_elements([element(1), element(1, name="Later Copy")])

    assert summary.created == 1
    assert db.session.scalars(select(Restaurant.name)).all() == ["Later Copy"]


def test_more_rows_than_one_batch(monkeypatch):
    monkeypatch.setattr(importer, "BATCH_SIZE", 2)

    import_elements([element(osm_id) for osm_id in range(1, 6)])

    assert count(Restaurant) == 5


def test_missing_places_are_kept_unless_pruning():
    import_elements([element(1), element(2)])

    kept = import_elements([element(1)])
    assert (kept.pruned, count(Restaurant)) == (0, 2)

    pruned = import_elements([element(1)], prune=True)
    assert (pruned.pruned, count(Restaurant)) == (1, 1)
    assert db.session.scalars(select(Restaurant.osm_id)).all() == [1]


def test_command_imports_what_overpass_returns(app, monkeypatch):
    monkeypatch.setattr(importer, "fetch_elements", lambda query: [element(1), element(2)])

    result = app.test_cli_runner().invoke(args=["import-osm"])

    assert result.exit_code == 0
    assert "2 created, 0 updated, 0 pruned" in result.output
    assert count(Restaurant) == 2


@pytest.mark.parametrize("args", [["import-osm"], ["import-osm", "--prune"]])
def test_command_changes_nothing_when_overpass_returns_no_places(app, monkeypatch, args):
    import_elements([element(1)])
    monkeypatch.setattr(importer, "fetch_elements", lambda query: [])

    result = app.test_cli_runner().invoke(args=args)

    assert result.exit_code != 0
    assert "nothing was changed" in result.output
    assert count(Restaurant) == 1


def test_command_reports_an_overpass_failure(app, monkeypatch):
    def fail(query):
        raise OverpassError("gave up")

    monkeypatch.setattr(importer, "fetch_elements", fail)

    result = app.test_cli_runner().invoke(args=["import-osm"])

    assert result.exit_code != 0
    assert "Overpass request failed: gave up" in result.output
