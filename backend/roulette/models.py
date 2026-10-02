"""Database tables."""

from datetime import datetime

from geoalchemy2 import Geography, WKTElement
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db

# The OSM `amenity` values the site treats as places to eat.
CATEGORIES = ("restaurant", "cafe", "fast_food", "pub", "bar")

# The diets the site can filter by, from OSM `diet:*` tags.
DIETS = ("vegetarian", "vegan", "halal", "kosher", "gluten_free")

# WGS 84: plain latitude/longitude, as used by GPS and OpenStreetMap.
SRID = 4326


def point(lat: float, lon: float) -> WKTElement:
    """Return a PostGIS point for a latitude/longitude pair.

    PostGIS, like most GIS software, orders coordinates x then y: longitude first.
    """
    return WKTElement(f"POINT({lon} {lat})", srid=SRID)


class Restaurant(db.Model):
    """One place to eat, imported from OpenStreetMap."""

    __tablename__ = "restaurants"
    __table_args__ = (
        # An OSM id is only unique within its element type, so the pair identifies a place.
        # The import upserts on this, which keeps `id` stable across re-imports.
        UniqueConstraint("osm_type", "osm_id", name="uq_restaurants_osm"),
        CheckConstraint(f"category IN {CATEGORIES}", name="category"),
        # GIN indexes make "array contains these values" filters indexable.
        Index("ix_restaurants_diets", "diets", postgresql_using="gin"),
        Index("ix_restaurants_cuisines", "cuisines", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    osm_type: Mapped[str] = mapped_column(Text)
    osm_id: Mapped[int] = mapped_column(BigInteger)

    name: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    # `geography` measures in metres over the earth's surface, unlike planar `geometry`.
    # GeoAlchemy2 creates a GiST spatial index on this column automatically.
    location: Mapped[WKTElement] = mapped_column(Geography("POINT", srid=SRID))

    cuisines: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    diets: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    # Raw OSM `opening_hours` text; NULL when OSM has none recorded.
    opening_hours: Mapped[str | None] = mapped_column(Text)

    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stored lower-cased, so the unique constraint is case-insensitive in effect.
    email: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    favourites: Mapped[list["Favourite"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class Favourite(db.Model):
    """A restaurant a user has saved. The composite primary key prevents duplicates."""

    __tablename__ = "favourites"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="favourites")
    restaurant: Mapped[Restaurant] = relationship()
