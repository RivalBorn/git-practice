from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import Task, User


todos_bp = Blueprint("todos", __name__)


@todos_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@todos_bp.post("/register")
def register():
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


@todos_bp.get("/tasks")
def list_tasks():
    tasks = Task.query.order_by(Task.id).all()
    return jsonify([{"id": task.id, "title": task.title} for task in tasks])