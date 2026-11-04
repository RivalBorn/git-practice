# API acceptance checklist

For a new database, run `flask --app wsgi db upgrade` before starting the app.
For an existing database whose schema exactly matches the baseline, stamp it
with `flask --app wsgi db stamp b0c5d7c6eb03` once, then run
`flask --app wsgi db upgrade`. Start the app with `flask --app wsgi run`, then
issue these requests to `http://127.0.0.1:5000`. Use the JWT returned by step 2
as `<token>` and the recipe ID returned by step 4 as `<id>`.

## Three-port service mode

The existing `wsgi:app` entry point remains available for the monolithic
acceptance run above. To run the split service surfaces, start each command in
a separate PowerShell terminal from the repository root, using the same
`JWT_SECRET` and `DATABASE_URL` in all three processes:

```powershell
.\venv\Scripts\python.exe wsgi_gateway.py
.\venv\Scripts\python.exe wsgi_users.py
.\venv\Scripts\python.exe wsgi_recipes.py
```

The gateway listens on port 5000, the users/auth service on 5001, and the
recipe service on 5002. `PORT` can override the listen port for each process.
The gateway forwards client requests to the respective service;
`USERS_SERVICE_URL` and `RECIPES_SERVICE_URL` configure their addresses. It
applies a 2-second HTTP timeout (`DOWNSTREAM_TIMEOUT_SECONDS` can override it).
It validates JWTs on protected requests before forwarding them; protected
routes in the receiving service validate the same JWT again. Both services
must be configured with the same signing secret for this HS256 setup.
All three processes currently use the same `DATABASE_URL` for compatibility
with the existing schema. This separates the HTTP/process boundaries, not
database ownership; recipe ownership and list scoping use the recipe's stored
`user_id` and the validated JWT ID without loading a SQLAlchemy user
relationship.

`GET http://127.0.0.1:5000/dashboard` is the composite endpoint: it fetches
the authenticated user's recipes and profile. If one downstream call fails,
the gateway returns the available component with `"partial": true` and an
`errors` entry for the unavailable component. The endpoint returns 503 only
when neither component can be fetched.

`GET http://127.0.0.1:5000/health` checks both downstream health endpoints.
When either service is unavailable or times out, the gateway returns HTTP 503
with `"status": "partial"`, `"partial": true`, and an individual status for
each service. A timed-out proxied API request returns HTTP 504 with
`{"error":"downstream timeout","service":"..."}`.

1. **Register Alice**
   - Request: `POST /register`
     ```powershell
     curl.exe -i -X POST http://127.0.0.1:5000/register `
       -H "Content-Type: application/json" `
       --data-raw '{"username":"alice","email":"alice@example.com","password":"test-password"}'
     ```
   - Expect: `201`; JSON includes `id`, `username: "alice"`, `email: "alice@example.com"`, and `role: "user"`.

2. **Log in as Alice**
   - Request: `POST /login`
     ```powershell
     curl.exe -i -X POST http://127.0.0.1:5000/login `
       -H "Content-Type: application/json" `
       --data-raw '{"username":"alice","password":"test-password"}'
     ```
   - Expect: `200`; JSON includes a JWT string in `token`.

3. **Get the current user**
   - Request:
     ```powershell
     curl.exe -i http://127.0.0.1:5000/me `
       -H "Authorization: Bearer <token>"
     ```
   - Expect: `200`; JSON includes Alice's `id`, `username: "alice"`, and `role: "user"`.

4. **Create a recipe**
   - Request:
     ```powershell
     curl.exe -i -X POST http://127.0.0.1:5000/recipes `
       -H "Authorization: Bearer <token>" `
       -H "Content-Type: application/json" `
       --data-raw '{"title":"Pasta","ingredients":"Pasta, tomatoes","cook_time_minutes":20}'
     ```
   - Expect: `201`; JSON includes `id`, `title`, `ingredients`,
     `cook_time_minutes`, and `user_id`.

5. **List recipes**
   - Request:
     ```powershell
     curl.exe -i http://127.0.0.1:5000/recipes `
       -H "Authorization: Bearer <token>"
     ```
   - Expect: `200`; JSON is an array containing the recipe created in step 4.

6. **Get the recipe**
   - Request:
     ```powershell
     curl.exe -i "http://127.0.0.1:5000/recipes/<id>" `
       -H "Authorization: Bearer <token>"
     ```
   - Expect: `200`; JSON contains the created recipe.

7. **Check recipe count**
   - Request:
     ```powershell
     curl.exe -i http://127.0.0.1:5000/recipes/count `
       -H "Authorization: Bearer <token>"
     ```
   - Expect: `200`; JSON contains `count`, at least `1` after step 4.

8. **Update the recipe**
   - Request:
     ```powershell
     curl.exe -i -X PUT "http://127.0.0.1:5000/recipes/<id>" `
       -H "Authorization: Bearer <token>" `
       -H "Content-Type: application/json" `
       --data-raw '{"title":"Updated Pasta","ingredients":"Pasta, tomatoes, basil","cook_time_minutes":25}'
     ```
   - Expect: `200`; JSON contains the same recipe ID and the updated values.

9. **Delete the recipe**
   - Request:
     ```powershell
     curl.exe -i -X DELETE "http://127.0.0.1:5000/recipes/<id>" `
       -H "Authorization: Bearer <token>"
     ```
   - Expect: `200`; JSON is `{"message":"recipe deleted"}`.

10. **Confirm the recipe is gone**
    - Request:
      ```powershell
      curl.exe -i "http://127.0.0.1:5000/recipes/<id>" `
        -H "Authorization: Bearer <token>"
      ```
    - Expect: `404`; JSON is `{"error":"recipe not found"}`.

11. **Access recipes without a token**
    - Request: `curl.exe -i http://127.0.0.1:5000/recipes`
    - Expect: `401`; JSON is `{"error":"authentication required"}`.

12. **Register with missing fields**
    - Request:
      ```powershell
      curl.exe -i -X POST http://127.0.0.1:5000/register `
        -H "Content-Type: application/json" `
        --data-raw '{"username":"bob"}'
      ```
    - Expect: `400`; JSON is
      `{"error":"username, email, and password are required"}`.

## Validation run

- Passed: 12/12.
- Executed the requests in order with Flask's test client against a temporary
  testing database; each status code and expected JSON fields/body matched.
- The run emitted a PyJWT warning that the configured HMAC signing key is
  shorter than the recommended 32 bytes.
- Current ORM, cache, and rate-limit tests are in
  `tests/test_design_features.py`; implementation details and measured evidence
  are in `DESIGN_EVIDENCE.md`.
