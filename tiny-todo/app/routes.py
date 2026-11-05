from flask import Blueprint, jsonify

from app.models import Task


todos_bp = Blueprint("todos", __name__)


@todos_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@todos_bp.get("/tasks")
def list_tasks():
    tasks = Task.query.order_by(Task.id).all()
    return jsonify([{"id": task.id, "title": task.title} for task in tasks])