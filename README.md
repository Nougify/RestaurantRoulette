# RestaurantRoulette

Can't decide where to eat? RestaurantRoulette picks a random place near you, filtered by distance, diet, cuisine and whether it is open right now, and shows it on a map.

> Work in progress: the database layer is in place; the data import, API and React frontend are next.

## Stack

| Layer | Technology |
| --- | --- |
| API | Python 3.13, Flask |
| Database | PostgreSQL 17 + PostGIS |
| Data access | SQLAlchemy 2, GeoAlchemy2, Alembic migrations |
| Data | OpenStreetMap (Metro Vancouver) |
| Frontend (planned) | React, TypeScript, Vite, Leaflet |

## Running locally

Requires Docker and Python 3.13.

```powershell
docker compose up -d --wait          # PostGIS on localhost:5433

cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1           # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
flask db upgrade                     # create the tables
python -m pytest                     # run the tests
```

No configuration is needed for local development; the defaults match `docker-compose.yml`. To point at a different database, copy `backend/.env.example` to `backend/.env`.

## Data

Restaurant data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, available under the Open Database License.
