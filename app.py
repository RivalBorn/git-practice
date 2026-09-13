import sqlite3
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta

app = Flask(__name__)

load_dotenv()
JWT_SECRET = os.getenv("JWT_SECRET")

DATABASE = "recipe.db"

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    with open("schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/register")
def register():
    data = request.get_json() or {}

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not email or not password:
        return jsonify({"error": "username, email, and password are required"}), 400

    password_hash = generate_password_hash(password)

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash),
        )
        conn.commit()
        user_id = cur.lastrowid
        conn.close()
    except sqlite3.IntegrityError:
        # username or email already taken
        return jsonify({"error": "username or email already in use"}), 409

    return (
        jsonify(
            {
                "id": user_id,
                "username": username,
                "email": email,
            }
        ),
        201,
    )

@app.post("/login")
def login():
    data = request.get_json() or {}

    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cur.fetchone()

    print("DEBUG username =", username, "user row =", user)

    auth_error = (jsonify({"error": "invalid username or password"}), 401)

    if user is None:
        print("DEBUG: no user found for", username)
        return auth_error

    ok = check_password_hash(user["password_hash"], password)
    print("DEBUG: password ok? =", ok)

    if not ok:
        return auth_error

    # at this point, credentials are correct

    # build the token payload
    payload = {
        "id": user["id"],
        "username": user["username"],
        "exp": datetime.utcnow() + timedelta(hours=1),
    }

    # sign the token
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    # return the token to the client
    return jsonify(
        {
            "token": token,
        }
    ), 200