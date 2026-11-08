# Recipe Box API

A small, working Flask + SQLite API for keeping recipes. Full CRUD, clean
status codes - and **no authentication at all**. Anyone who can reach it can
read, change, or delete anything. In BE104 you fix that: real users, hashed
passwords, JSON Web Tokens, ownership rules, and middleware.

## Run it

```
python init_db.py
python app.py
```

Requires Python 3.10+ and Flask (`pip install -r requirements.txt`).

## Run with Docker Compose

Docker Compose builds the API image, initializes the SQLite database on first
startup, and keeps the database in a named volume across container restarts.

```
docker compose up --build
```

The API is available at `http://localhost:8000`. To stop it, press `Ctrl+C`
and run `docker compose down`. The `recipes-data` volume is retained; removing
the volume with `docker compose down --volumes` deletes the database.

## Try it

```
curl http://127.0.0.1:5000/recipes
curl http://127.0.0.1:5000/recipes/1
curl -X POST http://127.0.0.1:5000/recipes -H "Content-Type: application/json" \
     -d '{"title": "Toast", "ingredients": "bread"}'
curl -X DELETE http://127.0.0.1:5000/recipes/1
```

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /recipes | 200 | |
| GET | /recipes/&lt;id&gt; | 200 | 404 |
| POST | /recipes | 201 | 400 bad body · 409 duplicate title |
| PATCH | /recipes/&lt;id&gt; | 200 | 400 · 404 · 409 |
| DELETE | /recipes/&lt;id&gt; | 204 | 404 |

`is_public` is stored on every recipe but nothing enforces it yet - by the end
of Unit 3, private recipes will only be visible to their owners.

Personal note: Cesar ran this API on my machine.
