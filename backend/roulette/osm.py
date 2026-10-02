"""Fetching places from OpenStreetMap's Overpass API and cleaning them into table rows."""

import time
from urllib.parse import urlsplit

import requests
import truststore

from .models import CATEGORIES, DIETS, point

# Verify HTTPS certificates against the operating system's certificate store, as browsers
# do, instead of the list bundled with `requests`. Needed on networks where a proxy or
# antivirus re-signs HTTPS traffic with its own locally trusted certificate.
truststore.inject_into_ssl()

# Public Overpass servers, tried in order. They are free and shared, so being told to
# come back later (429) or timing out under load (504) is normal.
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
RETRYABLE_STATUSES = {429, 502, 503, 504}
USER_AGENT = "RestaurantRoulette/0.1 (https://github.com/Nougify/RestaurantRoulette)"

# OSM relation 2218280 is the Metro Vancouver Regional District boundary. Overpass
# addresses the area enclosed by a relation as 3600000000 + the relation id.
METRO_VANCOUVER_AREA_ID = 3600000000 + 2218280

# OSM values that mean a diet is catered for: "yes" (some options) or "only" (nothing else).
DIET_YES = {"yes", "only"}


class OverpassError(Exception):
    """Overpass could not be reached or did not return a complete result."""


def build_query(area_id: int = METRO_VANCOUVER_AREA_ID) -> str:
    """Return the Overpass QL query for every named place to eat inside an area.

    `nwr` matches nodes, ways and relations: small places are mapped as a single point
    (node), larger ones as a building outline (way). `out center` adds one representative
    point for the outlines so everything can be stored as a point.
    """
    amenities = "|".join(CATEGORIES)
    return (
        "[out:json][timeout:180];"
        f"area(id:{area_id})->.region;"
        f'nwr["amenity"~"^({amenities})$"]["name"](area.region);'
        "out tags center;"
    )


def fetch_elements(query: str, attempts: int = 4, wait_seconds: float = 15) -> list[dict]:
    """Run `query` on Overpass and return its elements, retrying while servers are busy."""
    last_problem = "no attempt made"
    for attempt in range(attempts):
        url = OVERPASS_URLS[attempt % len(OVERPASS_URLS)]
        try:
            response = requests.post(
                url, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=240
            )
        except requests.RequestException as error:
            last_problem = f"{url}: {error}"
        else:
            if response.ok:
                payload = response.json()
                # Overpass reports a query that ran out of time or memory as HTTP 200
                # with a "remark" and partial data, which must not be imported.
                if "remark" in payload:
                    raise OverpassError(payload["remark"])
                return payload["elements"]
            if response.status_code not in RETRYABLE_STATUSES:
                raise OverpassError(f"{url}: HTTP {response.status_code}")
            last_problem = f"{url}: HTTP {response.status_code}"
        if attempt < attempts - 1:
            time.sleep(wait_seconds * (attempt + 1))
    raise OverpassError(f"gave up after {attempts} attempts; last problem: {last_problem}")


def clean_text(value: str | None) -> str | None:
    """Return `value` stripped of surrounding whitespace, or None if nothing is left."""
    return (value or "").strip() or None


def parse_cuisines(value: str | None) -> list[str]:
    """Split an OSM `cuisine` tag such as "Pizza; italian" into ["pizza", "italian"]."""
    cuisines = []
    for part in (value or "").split(";"):
        cuisine = part.strip().lower().replace(" ", "_")
        if cuisine and cuisine not in cuisines:
            cuisines.append(cuisine)
    return cuisines


def parse_diets(tags: dict) -> list[str]:
    """Return the diets from DIETS that the tags explicitly say are catered for."""
    return [diet for diet in DIETS if tags.get(f"diet:{diet}", "").strip().lower() in DIET_YES]


def parse_address(tags: dict) -> str | None:
    """Join the OSM `addr:*` tags into one line such as "123 Main Street, Vancouver"."""
    street = " ".join(
        part for key in ("addr:housenumber", "addr:street") if (part := clean_text(tags.get(key)))
    )
    return ", ".join(part for part in (street, clean_text(tags.get("addr:city"))) if part) or None


def parse_website(tags: dict) -> str | None:
    """Return the place's website as an http(s) URL, or None.

    The value ends up in a link on the site, so anything that is not plain http(s)
    (for example a `javascript:` URL) is dropped rather than trusted.
    """
    url = clean_text(tags.get("website")) or clean_text(tags.get("contact:website"))
    if url is None:
        return None
    if "://" not in url:
        url = "https://" + url
    try:
        parts = urlsplit(url)
        # Reading `.port` raises ValueError when the text after the host's colon is not a
        # number, which is how "javascript:alert(1)" looks once a scheme is put in front.
        valid = parts.scheme in ("http", "https") and bool(parts.hostname) and parts.port != 0
    except ValueError:
        return None
    return url if valid else None


def parse_element(element: dict) -> dict | None:
    """Turn one Overpass element into a `restaurants` row, or None if it is unusable."""
    tags = element.get("tags", {})
    name = clean_text(tags.get("name"))
    category = tags.get("amenity")
    # Nodes carry their own coordinates; ways and relations carry a computed "center".
    position = element if element.get("type") == "node" else element.get("center", {})
    lat, lon = position.get("lat"), position.get("lon")

    if name is None or category not in CATEGORIES or lat is None or lon is None:
        return None

    return {
        "osm_type": element["type"],
        "osm_id": element["id"],
        "name": name,
        "category": category,
        "location": point(lat, lon),
        "cuisines": parse_cuisines(tags.get("cuisine")),
        "diets": parse_diets(tags),
        "opening_hours": clean_text(tags.get("opening_hours")),
        "address": parse_address(tags),
        "phone": clean_text(tags.get("phone")) or clean_text(tags.get("contact:phone")),
        "website": parse_website(tags),
    }
