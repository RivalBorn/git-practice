from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    # Report that the API process is responding.
    return jsonify({"status": "ok"}), 200
