# Recipe Box API

A Flask + SQLite API for keeping recipes. Users register and log in to receive
a bearer token. Recipes are assigned to their creator; authenticated users can
only list, read, update, or delete their own recipes.

## Run it

```
python init_db.py
python recipe_api.py
```

Requires Python 3.10+ (`pip install -r requirements.txt`).
Set `JWT_SECRET_KEY` to a long, random value before starting the API if tokens
must remain valid across restarts. If it is not set, the app generates a
temporary secret at startup, so previously issued tokens stop working after a
restart.

Existing and seeded recipes have no owner and are deliberately hidden from
user endpoints until an administrator assigns them an owner.

## Run with Docker Compose

Docker Compose builds the API image, initializes the SQLite database on first
startup, and keeps the database in a named volume across container restarts.

```
docker compose up --build
```

The API is available at `http://localhost:8000`. To stop it, press `Ctrl+C`
and run `docker compose down`. The `recipes-data` volume is retained; removing
the volume with `docker compose down --volumes` deletes the database.
Set `JWT_SECRET_KEY` in the environment before starting Compose to keep tokens
valid across container restarts.

## Try it

Set a secret in PowerShell before starting the API:

```
$env:JWT_SECRET_KEY = "<long-random-secret>"
python init_db.py
python recipe_api.py
```

In another terminal, register users and log in to get their tokens:

```
curl.exe -X POST http://127.0.0.1:5000/register -H "Content-Type: application/json" --data-raw "{\"username\":\"alice\",\"password\":\"a-long-password\"}"
curl.exe -X POST http://127.0.0.1:5000/login -H "Content-Type: application/json" --data-raw "{\"username\":\"alice\",\"password\":\"a-long-password\"}"
curl.exe -X POST http://127.0.0.1:5000/recipes -H "Authorization: Bearer <token>" -H "Content-Type: application/json" --data-raw "{\"title\":\"Toast\",\"ingredients\":\"bread\"}"
curl.exe http://127.0.0.1:5000/recipes/1 -H "Authorization: Bearer <token>"
```

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| POST | /register | 201 | 400 invalid details · 409 username exists |
| POST | /login | 200 | 401 invalid credentials |
| GET | /recipes | 200 | 401 missing or invalid token |
| GET | /recipes/&lt;id&gt; | 200 | 400 invalid ID · 401 · 403 not owned · 404 missing |
| POST | /recipes | 201 | 400 bad body · 401 · 409 duplicate title |
| PATCH | /recipes/&lt;id&gt; | 200 | 400 · 401 · 404 missing or not owned · 409 |
| DELETE | /recipes/&lt;id&gt; | 204 | 401 · 404 missing or not owned |

`is_public` is retained as recipe data but does not make a recipe visible to
other users; ownership is required for every recipe read or change.

Personal note: Cesar ran this API on my machine.

The original Maestro course application from GitHub remains in the `app/`
package and its related files.
