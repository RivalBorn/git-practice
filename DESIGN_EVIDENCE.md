# Week 2 Design and Evidence Report

## Models

`User` in `app/models.py` has `id`, `username`, `email`, `password_hash`, and
`role`. `Recipe` has `id`, `title`, `ingredients`, `cook_time_minutes`,
`user_id`, and the new nullable `notes` field. `Recipe.user_id` is a
non-nullable foreign key to `users.id`. No ORM relationships are declared;
ownership checks use `Recipe.user_id` directly.

This replaces BE104's manual SQLite-row ownership lookup with an ORM model
check: recipe GET and PUT verify `recipe.user_id` against the authenticated
user ID; DELETE applies the same owner check while retaining the existing admin
exception. Recipe-list queries remain scoped by `user_id`. SQLite foreign-key
enforcement is enabled for application connections.

## Migration evidence

Alembic/Flask-Migrate is configured in the app factory. The command sequence
used an isolated SQLite database, not the project's local recipe databases:

```powershell
flask --app wsgi db init
flask --app wsgi db migrate -m "baseline schema"
# Simulate a pre-Alembic database already at the baseline schema:
.\venv\Scripts\python.exe -c "from wsgi import app; from app.extensions import db; app.app_context().push(); db.create_all()"
flask --app wsgi db stamp b0c5d7c6eb03
# Add Recipe.notes to the model, then generate/apply its migration:
flask --app wsgi db migrate -m "add optional recipe notes"
flask --app wsgi db upgrade
```

The baseline is revision `b0c5d7c6eb03` in
`migrations/versions/b0c5d7c6eb03_baseline_schema.py`. The generated model
change is revision `92140465ffd9` in
`migrations/versions/92140465ffd9_add_optional_recipe_notes.py`. Its upgrade
adds one nullable `TEXT` column, `recipes.notes`; its downgrade drops that
column. `flask db check` reported no ungenerated model changes after upgrade.

For the empty-database proof, `flask --app wsgi db upgrade` was run against a
second, newly created SQLite file. SQLAlchemy metadata and SQLite inspection
reported identical columns (`schema_equal=True`):

```text
users:   email, id, password_hash, role, username
recipes: cook_time_minutes, id, ingredients, notes, title, user_id
```

An existing database should only be stamped at the baseline if its schema
already matches that baseline; new empty databases should use `db upgrade`
without stamping.

## Cache decision

The authenticated `GET /recipes` list is cached with Flask-Caching's
`SimpleCache`, using a per-user key and a 30-second TTL. On the local
development server, measured with `curl.exe -w "%{time_total}"`:

| Request | Status | Time |
| --- | ---: | ---: |
| Cold `GET /recipes` (database read, empty list) | 200 | 0.006080 s (6.080 ms) |
| Warm `GET /recipes` (cache hit) | 200 | 0.002358 s (2.358 ms) |

The tradeoff is that changes made outside this API process can remain
invisible for up to 30 seconds. API recipe create, update, and delete
operations explicitly invalidate the affected user's list immediately.
The following PowerShell `curl.exe` sequence primes the cache, writes a recipe,
then confirms the next read includes it (JSON is escaped for Windows native
argument parsing):

```powershell
$base = 'http://127.0.0.1:5000'
$register = @{ username='cache-proof'; email='cache-proof@example.test'; password='test-password' } | ConvertTo-Json -Compress
$register = $register.Replace('"','\"')
curl.exe -sS --data-raw "$register" -H 'Content-Type: application/json' "$base/register"

$login = @{ username='cache-proof'; password='test-password' } | ConvertTo-Json -Compress
$login = $login.Replace('"','\"')
$token = (curl.exe -sS --data-raw "$login" -H 'Content-Type: application/json' "$base/login" | ConvertFrom-Json).token

# Prime the per-user list cache.
curl.exe -sS "$base/recipes" -H "Authorization: Bearer $token"

# Write, then immediately read the same cached list.
$recipe = @{ title='CacheProof'; ingredients='Beans'; cook_time_minutes=20; notes='Fresh' } | ConvertTo-Json -Compress
$recipe = $recipe.Replace('"','\"')
curl.exe -sS --data-raw "$recipe" -H "Authorization: Bearer $token" -H 'Content-Type: application/json' -X POST "$base/recipes"
curl.exe -sS "$base/recipes" -H "Authorization: Bearer $token"
```

The recorded sequence returned `201` for the write and `200` for the following
list read; the list contained the newly created recipe rather than the cached
empty list.

## Limit decision

`POST /register` and `POST /login` each have a limit of five requests per
minute, keyed by remote address. These credential/account-creation endpoints
are the highest-value places to constrain brute-force and automated abuse.
The observed evidence was five allowed malformed registration attempts
returning `400`, followed by the sixth returning **`429`** with
`{"error":"rate limit exceeded"}`.

Recipe reads are not rate-limited. They require a valid JWT and the list is
scoped to the authenticated owner; they are also a normal, frequent API
operation and the list cache helps reduce repeated database work. The cache and
rate-limit stores are in-memory per process, appropriate for this local
project but not shared across multiple production workers.

## Automated verification

`python -m unittest discover -s tests -p 'test_design_features.py' -v`
passed four tests covering the ORM foreign key without relationships, cached
read reuse and invalidation after writes, the `429` response, and unrestricted
recipe reads.
