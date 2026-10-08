# RestaurantRoulette

Can't decide where to eat? Spin, and RestaurantRoulette deals you up to five random places near you, filtered by distance, diet, cuisine and whether they are open right now, and shows them on a map. Sign up to save favourites.

> https://nougify.github.io/RestaurantRoulette/

## Stack

| Layer | Technology |
| --- | --- |
| API | Python 3.13, Flask, Pydantic |
| Auth | Argon2id password hashing, JWT bearer tokens |
| Database | PostgreSQL 17 + PostGIS |
| Data access | SQLAlchemy 2, GeoAlchemy2, Alembic migrations |
| Data | OpenStreetMap (Metro Vancouver) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router, Leaflet |

## Running locally

Requires Docker, Python 3.13 and Node 24. Use two terminals: one for the API, one for the frontend.

```powershell
docker compose up -d --wait          # PostGIS on localhost:5433

cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1           # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
flask db upgrade                     # create the tables
flask import-osm                     # load Metro Vancouver's restaurants, cafes and fast food
python -m pytest                     # run the tests
flask run --debug                    # API on http://localhost:5000
```

```powershell
cd frontend
npm install
npm run dev                          # app on http://localhost:5173
```

No configuration is needed for local development; the defaults match `docker-compose.yml`. Copy `backend/.env.example` to `backend/.env` to change the database, set `SECRET_KEY` (so logins survive a server restart) or allow other frontend origins. The frontend reads the API's address from `VITE_API_URL` (see `frontend/.env.example`).

## API

All routes are under `/api` and return JSON.

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/health` | | Server and database are reachable |
| GET | `/api/restaurants/nearby` | | Matching places, nearest first |
| GET | `/api/restaurants/spin` | | Up to `count` random matching places |
| GET | `/api/filters` | | Categories, diets and the most common cuisines |
| POST | `/api/auth/register` | | Create an account; returns a token |
| POST | `/api/auth/login` | | Returns a token |
| GET | `/api/auth/me` | Bearer | The signed-in user |
| GET | `/api/favourites` | Bearer | Saved places, newest first |
| PUT | `/api/favourites/<id>` | Bearer | Save a place |
| DELETE | `/api/favourites/<id>` | Bearer | Remove a saved place |

Search parameters for `nearby` and `spin`:

| Parameter | Meaning |
| --- | --- |
| `lat`, `lon` | Required. Where to search from |
| `radius` | Metres; default 2000, maximum 25000 |
| `category` | Any of `restaurant`, `cafe`, `fast_food` (comma-separated) |
| `cuisine` | Any of the listed cuisines, e.g. `sushi,pizza` |
| `diet` | `vegetarian`, `vegan`, `halal`, `kosher`, `gluten_free` (comma-separated) |
| `diet_match` | `all` (default): every listed diet; `any`: at least one |
| `open_now` | `true` to keep only places known to be open right now |
| `limit` | `nearby` only; default 50, maximum 200 |
| `count` | `spin` only; how many places, 1 to 5 (default 1) |
| `seen` | `spin` only; ids shown in earlier spins. At most one of them is picked again |

Only explicit data counts: a place with no diet tags or no recorded opening hours never matches those filters.

```
GET /api/restaurants/spin?lat=49.2829&lon=-123.1207&radius=800&diet=vegan&open_now=true&count=3
```

Errors share one shape, for example a `422`:

```json
{"error": {"code": "validation_error", "message": "Some values are not valid.",
           "details": [{"field": "radius", "message": "Input should be less than or equal to 25000"}]}}
```

## Data

`flask import-osm` downloads every named restaurant, cafe and fast-food place in Metro Vancouver (about 6,800) from OpenStreetMap through the Overpass API. It is safe to re-run: existing places are updated in place rather than duplicated. Pass `--prune` to also delete places that OpenStreetMap no longer lists.

Restaurant data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, available under the Open Database License.
