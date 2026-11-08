"""Recipe Box API with bearer-token authentication and recipe ownership."""

import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Flask, current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

DATABASE = os.environ.get("DATABASE_PATH", "recipes.db")

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.environ.get(
    "JWT_SECRET_KEY"
) or secrets.token_urlsafe(32)
app.config["JWT_LIFETIME_SECONDS"] = int(
    os.environ.get("JWT_LIFETIME_SECONDS", "3600")
)


@app.errorhandler(404)
def handle_not_found(error):
    return jsonify({"error": error.name.lower()}), 404


@app.errorhandler(400)
def handle_bad_request(error):
    return jsonify({"error": error.name.lower()}), 400


@app.errorhandler(403)
def handle_forbidden(error):
    return jsonify({"error": error.name.lower()}), 403


def token_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        authorization = request.headers.get("Authorization", "").split()
        if (
            len(authorization) != 2
            or authorization[0].casefold() != "bearer"
        ):
            return jsonify({"error": "a valid bearer token is required"}), 401

        try:
            payload = jwt.decode(
                authorization[1],
                current_app.config["JWT_SECRET_KEY"],
                algorithms=["HS256"],
                options={"require": ["exp", "sub"]},
            )
        except jwt.InvalidTokenError:
            return jsonify({"error": "a valid bearer token is required"}), 401

        if not isinstance(payload, dict):
            return jsonify({"error": "a valid bearer token is required"}), 401

        subject = payload.get("sub")
        if (
            not isinstance(subject, str)
            or not subject.isascii()
            or not subject.isdecimal()
        ):
            return jsonify({"error": "a valid bearer token is required"}), 401
        user_id = int(subject)
        if user_id <= 0:
            return jsonify({"error": "a valid bearer token is required"}), 401

        g.user_id = user_id
        return view(*args, **kwargs)

    return wrapped


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def recipe_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "ingredients": row["ingredients"],
        "instructions": row["instructions"],
        "is_public": bool(row["is_public"]),
    }


def owned_recipe(recipe_id):
    return get_db().execute(
        "SELECT * FROM recipes WHERE id = ? AND owner_id = ?",
        (recipe_id, g.user_id),
    ).fetchone()


@app.get("/")
def hello():
    return jsonify({
        "message": "Recipe Box API",
        "recipes": "/recipes",
        "register": "/register",
        "login": "/login",
    })


@app.post("/register")
def register():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "username and password are required"}), 400

    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not username.strip():
        return jsonify({"error": "username is required"}), 400
    username = username.strip()
    if len(username) < 3 or len(username) > 30:
        return jsonify({"error": "username must be 3 to 30 characters"}), 400
    if not isinstance(password, str) or len(password) < 8 or len(password) > 128:
        return jsonify({"error": "password must be 8 to 128 characters"}), 400

    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({"error": "username is already registered"}), 409

    return jsonify({"id": cur.lastrowid, "username": username}), 201


@app.post("/login")
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "invalid username or password"}), 401

    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "invalid username or password"}), 401

    user = get_db().execute(
        "SELECT id, password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "invalid username or password"}), 401

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user["id"]),
            "exp": now + timedelta(
                seconds=current_app.config["JWT_LIFETIME_SECONDS"]
            ),
        },
        current_app.config["JWT_SECRET_KEY"],
        algorithm="HS256",
    )
    return jsonify({"token": token}), 200


@app.get("/recipes")
@token_required
def list_recipes():
    rows = get_db().execute(
        "SELECT * FROM recipes WHERE owner_id = ? ORDER BY id",
        (g.user_id,),
    ).fetchall()
    return jsonify([recipe_to_dict(r) for r in rows])


@app.get("/recipes/<recipe_id>")
@token_required
def get_recipe(recipe_id):
    if (
        not recipe_id.isascii()
        or not recipe_id.isdecimal()
        or int(recipe_id) <= 0
    ):
        return jsonify({"error": "recipe id must be a positive integer"}), 400

    db = get_db()
    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (int(recipe_id),)
    ).fetchone()
    if row is None:
        return jsonify({"error": "recipe not found"}), 404
    if row["owner_id"] != g.user_id:
        return jsonify({"error": "forbidden"}), 403
    return jsonify(recipe_to_dict(row))


@app.post("/recipes")
@token_required
def create_recipe():
    data = request.get_json(silent=True)
    if (
        not isinstance(data, dict)
        or not data.get("title")
        or not data.get("ingredients")
    ):
        return jsonify({"error": "title and ingredients are required"}), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO recipes "
            "(title, ingredients, instructions, is_public, owner_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                data["title"],
                data["ingredients"],
                data.get("instructions", ""),
                1 if data.get("is_public", True) else 0,
                g.user_id,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "a recipe with that title already exists"}), 409
    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    return jsonify(recipe_to_dict(row)), 201


@app.patch("/recipes/<int:recipe_id>")
@token_required
def update_recipe(recipe_id):
    if owned_recipe(recipe_id) is None:
        return jsonify({"error": "recipe not found"}), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "a JSON body is required"}), 400
    fields, values = [], []
    for column in ("title", "ingredients", "instructions"):
        if column in data:
            fields.append(f"{column} = ?")
            values.append(data[column])
    if "is_public" in data:
        fields.append("is_public = ?")
        values.append(1 if data["is_public"] else 0)
    if not fields:
        return jsonify({"error": "nothing to update"}), 400
    values.extend((recipe_id, g.user_id))
    db = get_db()
    try:
        cur = db.execute(
            f"UPDATE recipes SET {', '.join(fields)} "
            "WHERE id = ? AND owner_id = ?",
            values,
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "a recipe with that title already exists"}), 409
    if cur.rowcount == 0:
        return jsonify({"error": "recipe not found"}), 404
    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?", (recipe_id,)
    ).fetchone()
    return jsonify(recipe_to_dict(row))


@app.delete("/recipes/<int:recipe_id>")
@token_required
def delete_recipe(recipe_id):
    db = get_db()
    cur = db.execute(
        "DELETE FROM recipes WHERE id = ? AND owner_id = ?",
        (recipe_id, g.user_id),
    )
    db.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "recipe not found"}), 404
    return "", 204


if __name__ == "__main__":
    app.run(debug=True)
