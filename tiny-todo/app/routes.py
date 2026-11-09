"""Define the HTTP routes for the Tiny Todo API."""

from datetime import datetime, timedelta, timezone

import jwt
from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.auth import token_required
from app.extensions import db
from app.models import Task, User


todos_bp = Blueprint("todos", __name__)


@todos_bp.get("/health")
def health():
    """Return a simple status response to confirm the API is available."""
    return jsonify({"status": "ok"})


@todos_bp.post("/register")
def register():
    """Validate registration details and create a new user."""
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not username.strip():
        return jsonify({
            "code": "VALIDATION_ERROR",
            "message": "Username is required.",
        }), 400

    if not isinstance(password, str) or not password.strip():
        return jsonify({
            "code": "VALIDATION_ERROR",
            "message": "Password is required.",
        }), 400

    if len(username) < 3 or len(username) > 30:
        return jsonify({
            "code": "VALIDATION_ERROR",
            "message": "Username must be between 3 and 30 characters long.",
        }), 400

    if len(password) < 8 or len(password) > 64:
        return jsonify({
            "code": "VALIDATION_ERROR",
            "message": "Password must be between 8 and 64 characters long.",
        }), 400

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({
            "code": "USERNAME_TAKEN",
            "message": "That username is already in use.",
        }), 409

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if User.query.filter_by(username=username).first():
            return jsonify({
                "code": "USERNAME_TAKEN",
                "message": "That username is already in use.",
            }), 409
        raise

    return jsonify({"id": user.id, "username": user.username}), 201


@todos_bp.post("/login")
def login():
    """Verify a user's credentials and return a generic authentication error on failure."""
    data = request.get_json(silent=True) or {}
    username = data.get("username") if isinstance(data, dict) else None
    password = data.get("password") if isinstance(data, dict) else None

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({
            "code": "INVALID_CREDENTIALS",
            "message": "Invalid username or password.",
        }), 401

    user = User.query.filter_by(username=username).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return jsonify({
            "code": "INVALID_CREDENTIALS",
            "message": "Invalid username or password.",
        }), 401

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": now + timedelta(
            seconds=current_app.config["JWT_LIFETIME_SECONDS"]
        ),
    }
    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET_KEY"],
        algorithm="HS256",
    )
    return jsonify({"token": token}), 200


@todos_bp.post("/tasks")
@token_required
def create_task():
    data = request.get_json(silent=True) or {}
    title = data.get("title") if isinstance(data, dict) else None
    if not isinstance(title, str) or not title.strip():
        return jsonify({
            "code": "VALIDATION_ERROR",
            "message": "Task title is required.",
        }), 400

    task = Task(title=title.strip(), user_id=g.user_id)
    db.session.add(task)
    db.session.commit()
    return jsonify({"id": task.id, "title": task.title}), 201


@todos_bp.get("/tasks")
@token_required
def list_tasks():
    """Return the authenticated user's tasks ordered by their database IDs."""
    tasks = (
        Task.query.filter_by(user_id=g.user_id)
        .order_by(Task.id)
        .all()
    )
    return jsonify([{"id": task.id, "title": task.title} for task in tasks])


@todos_bp.get("/tasks/<int:task_id>")
@token_required
def get_task(task_id):
    """Return a task by ID, or a not-found error if it does not exist."""
    task = db.session.get(Task, task_id)
    if task is None:
        return jsonify({
            "code": "TASK_NOT_FOUND",
            "message": "The requested task was not found.",
        }), 404

    return jsonify({"id": task.id, "title": task.title}), 200


@todos_bp.get("/profile")
@token_required
def get_profile():
    """Return the authenticated user's public profile."""
    user = User.query.filter_by(id=g.user_id).first()
    if user is None:
        return jsonify({
            "code": "USER_NOT_FOUND",
            "message": "The user associated with this token was not found.",
        }), 404

    return jsonify({"id": user.id, "username": user.username})


@todos_bp.patch("/profile")
@token_required
def update_profile():
    """Update the authenticated user's username."""
    user = User.query.filter_by(id=g.user_id).first()
    if user is None:
        return jsonify({
            "code": "USER_NOT_FOUND",
            "message": "The user associated with this token was not found.",
        }), 404

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"username"}:
        return jsonify({
            "code": "VALIDATION_ERROR",
            "message": "Only the username field may be updated.",
        }), 400

    username = data["username"]
    if not isinstance(username, str) or not username.strip():
        return jsonify({
            "code": "VALIDATION_ERROR",
            "message": "Username is required.",
        }), 400

    if len(username) < 3 or len(username) > 30:
        return jsonify({
            "code": "VALIDATION_ERROR",
            "message": "Username must be between 3 and 30 characters long.",
        }), 400

    existing_user = User.query.filter(
        User.username == username,
        User.id != user.id,
    ).first()
    if existing_user:
        return jsonify({
            "code": "USERNAME_TAKEN",
            "message": "That username is already in use.",
        }), 409

    user.username = username
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if User.query.filter(
            User.username == username,
            User.id != user.id,
        ).first():
            return jsonify({
                "code": "USERNAME_TAKEN",
                "message": "That username is already in use.",
            }), 409
        raise

    return jsonify({"id": user.id, "username": user.username})


@todos_bp.get("/admin/ping")
# token check
@token_required
def admin_ping():
    """Return a status response to authenticated administrators."""
    user = User.query.filter_by(id=g.user_id).first()
    if user is None:
        return jsonify({
            "code": "USER_NOT_FOUND",
            "message": "The user associated with this token was not found.",
        }), 404

    # role check
    if user.role != "admin":
        return jsonify({
            "code": "FORBIDDEN",
            "message": "Administrator access is required.",
        }), 403

    return jsonify({"status": "ok"}), 200