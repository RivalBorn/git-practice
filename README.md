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

1. Clone the repository and enter its folder:

   ```
   git clone https://github.com/RivalBorn/git-practice.git
   cd git-practice
   ```

2. Create your local environment file:

   ```
   Copy-Item .env.example .env
   ```

   Edit `.env` and replace the `JWT_SECRET` placeholder with a strong random
   secret. Keep `.env` private.

3. Build and start the API and PostgreSQL:

   ```
   docker compose up --build
   ```

   The API container runs database migrations at startup. In another terminal,
   you can also run them explicitly:

   ```
   docker compose exec api flask --app wsgi db upgrade
   ```

4. Check that the API responds at `http://localhost:8000/health`. To register
   and log in, send JSON requests to `/register` and `/login`; use the returned
   bearer token for protected recipe endpoints such as `/recipes`.

5. Stop the stack with `Ctrl+C`, then run:

   ```
   docker compose down
   ```

   The `postgres-data` named volume keeps database contents when containers
   are stopped or recreated. To delete the database too, run
   `docker compose down --volumes`.

The standalone `python recipe_api.py` command above remains the SQLite-based
API; Compose runs the Flask application in `app/`.

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
