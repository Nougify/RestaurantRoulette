"""Loading cleaned OpenStreetMap places into the database."""

from dataclasses import dataclass
from itertools import batched

import click
from flask import Flask
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from .extensions import db
from .models import Restaurant
from .osm import OverpassError, build_query, fetch_elements, parse_element

# Rows per INSERT statement. Postgres allows 65,535 bound parameters per statement
# and each row uses 11, so this stays well under the limit.
BATCH_SIZE = 1000

KEY_COLUMNS = ("osm_type", "osm_id")


@dataclass
class ImportSummary:
    received: int = 0
    skipped: int = 0
    created: int = 0
    updated: int = 0
    pruned: int = 0


def existing_keys() -> dict[tuple[str, int], int]:
    """Return {(osm_type, osm_id): id} for every restaurant already stored."""
    rows = db.session.execute(select(Restaurant.osm_type, Restaurant.osm_id, Restaurant.id))
    return {(osm_type, osm_id): id_ for osm_type, osm_id, id_ in rows}


def upsert(rows: list[dict]) -> None:
    """Insert `rows`, updating the stored row instead where the OSM element already exists."""
    for batch in batched(rows, BATCH_SIZE, strict=False):
        statement = insert(Restaurant).values(batch)
        # `excluded` is Postgres's name for the row that failed to insert.
        changes = {
            column: statement.excluded[column] for column in batch[0] if column not in KEY_COLUMNS
        }
        db.session.execute(
            statement.on_conflict_do_update(constraint="uq_restaurants_osm", set_=changes)
        )


def import_elements(elements: list[dict], prune: bool = False) -> ImportSummary:
    """Clean Overpass `elements` and store them, all in one transaction.

    Running it again with the same data changes nothing (it is idempotent). With `prune`,
    stored restaurants that are no longer in `elements` are deleted.
    """
    summary = ImportSummary(received=len(elements))

    # Keyed by OSM identity so an element repeated in the input is only written once.
    rows = {}
    for element in elements:
        row = parse_element(element)
        if row is None:
            summary.skipped += 1
        else:
            rows[(row["osm_type"], row["osm_id"])] = row

    before = existing_keys()
    upsert(list(rows.values()))
    summary.updated = len(rows.keys() & before.keys())
    summary.created = len(rows) - summary.updated

    if prune:
        stale_ids = [id_ for key, id_ in before.items() if key not in rows]
        for batch in batched(stale_ids, BATCH_SIZE, strict=False):
            db.session.execute(delete(Restaurant).where(Restaurant.id.in_(batch)))
        summary.pruned = len(stale_ids)

    db.session.commit()
    return summary


@click.command("import-osm")
@click.option(
    "--prune",
    is_flag=True,
    help="Also delete stored places that OpenStreetMap no longer lists (and their favourites).",
)
def import_osm_command(prune: bool) -> None:
    """Import Metro Vancouver's places to eat from OpenStreetMap."""
    click.echo("Fetching from Overpass (this can take a minute)...")
    try:
        elements = fetch_elements(build_query())
    except OverpassError as error:
        raise click.ClickException(f"Overpass request failed: {error}") from error
    if not elements:
        raise click.ClickException("Overpass returned no places; nothing was changed.")

    summary = import_elements(elements, prune=prune)
    click.echo(
        f"Received {summary.received}, skipped {summary.skipped}: "
        f"{summary.created} created, {summary.updated} updated, {summary.pruned} pruned."
    )


def register_commands(app: Flask) -> None:
    app.cli.add_command(import_osm_command)
