# Authentication security test

Evidence captured from the local Tiny Todo API and its SQLite database.
The test account was created for this check; no plaintext test password is
included here.

## Stored password

Query:

```sql
SELECT id, username, password_hash, created_at
FROM user
WHERE username = 'test-proof-21edad2a';
```

Result:

```text
id: 5
username: test-proof-21edad2a
password_hash: scrypt:32768:8:1$uin0c3q4z9i39tbd$9de4ff920aaaa5dabec34571cfa17623f983db606e313e4f5cd46016adc9d22d3978c4ad2594a422593796e55736e8195209665a7d465b6a6a814aa273d3198e
created_at: 2026-11-08 01:07:08
```

The stored value is a salted scrypt password hash, not the password. Recomputing
scrypt with the temporary test password matched this stored value; the password
itself was not recorded.

## Wrong-password login

Command:

```powershell
curl.exe -i -sS -X POST http://127.0.0.1:5003/api/login -H "Content-Type: application/json" -d '{"username":"test-proof-21edad2a","password":"totally-wrong-password-123"}'
```

Response:

```http
HTTP/1.1 401 UNAUTHORIZED
Server: Werkzeug/3.1.8 Python/3.11.9
Date: Sun, 08 Nov 2026 01:09:15 GMT
Content-Type: application/json
Content-Length: 73
Connection: close

{"code":"INVALID_CREDENTIALS","message":"Invalid username or password."}
```
