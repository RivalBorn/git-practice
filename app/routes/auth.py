from functools import wraps

import jwt
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.extensions import db, limiter
from app.models import User
from app.services.auth_service import authenticate_user, register_user

auth_bp = Blueprint("auth", __name__)


# Reject requests unless they carry a valid bearer JWT.
def require_auth(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        parts = auth_header.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"error": "authentication required"}), 401

        token = parts[1]

        try:
            payload = jwt.decode(
                token,
                current_app.config["JWT_SECRET"],
                algorithms=["HS256"],
            )

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return jsonify({"error": "authentication required"}), 401

        return view_func(payload, *args, **kwargs)

    return wrapped


# Require a valid token whose role claim identifies an administrator.
def require_admin(view_func):
    @wraps(view_func)
    @require_auth
    def wrapped(payload, *args, **kwargs):
        if payload.get("role") != "admin":
            return jsonify({"error": "forbidden"}), 403

        return view_func(payload, *args, **kwargs)

    return wrapped


@auth_bp.post("/register")
@limiter.limit("5 per minute")
def register():
    # Parse JSON input, using an empty object when no JSON body is provided.
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    # Require all fields needed to create an account.
    if not username or not email or not password:
        return jsonify(
            {
                "error": "username, email, and password are required"
            }
        ), 400

    try:
        user = register_user(username, email, password)

    except IntegrityError:
        db.session.rollback()
        return jsonify(
            {
                "error": "username or email already in use"
            }
        ), 409

    return jsonify(user), 201


@auth_bp.post("/login")
@limiter.limit("5 per minute")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify(
            {
                "error": "username and password are required"
            }
        ), 400

    token = authenticate_user(username, password)
    if token is None:
        return jsonify(
            {
                "error": "invalid username or password"
            }
        ), 401

    return jsonify({"token": token}), 200


@auth_bp.get("/me")
@require_auth
def get_me(payload):
    return jsonify(
        {
            "id": payload["id"],
            "username": payload["username"],
            "role": payload["role"],
        }
    ), 200


@auth_bp.get("/users")
@require_admin
def list_users(payload):
    users = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }
        for user in User.query.order_by(User.id).all()
    ]

    return jsonify(users), 200


@auth_bp.post("/users")
@require_admin
def create_user(payload):
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify(
            {
                "error": "username, email, and password are required"
            }
        ), 400

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password),
        role="user",
    )
    db.session.add(user)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(
            {
                "error": "username or email already in use"
            }
        ), 409

    return jsonify(
        {
            "id": user.id,
            "username": username,
            "email": email,
            "role": "user",
        }
    ), 201


@auth_bp.post("/secret-note")
@require_auth
def secret_note(payload):
    return jsonify(
        {
            "message": "You reached the secret zone!"
        }
    ), 200


@auth_bp.post("/make-admin")
@require_admin
def make_admin(payload):
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()

    if not username:
        return jsonify(
            {
                "error": "username is required"
            }
        ), 400

    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify({"error": "user not found"}), 404

    user.role = "admin"
    db.session.commit()

    return jsonify(
        {
            "message": f"{username} is now admin"
        }
    ), 200
