"""Authentication helpers for protected API routes."""

from functools import wraps

import jwt
from flask import current_app, g, jsonify, request


def token_required(view):
    """Require a valid Bearer JWT before calling the decorated route."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        authorization = request.headers.get("Authorization", "").split()
        if (
            len(authorization) != 2
            or authorization[0].casefold() != "bearer"
        ):
            return jsonify({
                "code": "INVALID_TOKEN",
                "message": "A valid bearer token is required.",
            }), 401

        try:
            payload = jwt.decode(
                authorization[1],
                current_app.config["JWT_SECRET_KEY"],
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            return jsonify({
                "code": "TOKEN_EXPIRED",
                "message": "The token has expired.",
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "code": "INVALID_TOKEN",
                "message": "A valid bearer token is required.",
            }), 401

        subject = payload.get("sub") if isinstance(payload, dict) else None
        if not isinstance(subject, str):
            return jsonify({
                "code": "INVALID_TOKEN",
                "message": "A valid bearer token is required.",
            }), 401

        try:
            user_id = int(subject)
        except ValueError:
            return jsonify({
                "code": "INVALID_TOKEN",
                "message": "A valid bearer token is required.",
            }), 401

        if user_id <= 0:
            return jsonify({
                "code": "INVALID_TOKEN",
                "message": "A valid bearer token is required.",
            }), 401

        g.user_id = user_id
        return view(*args, **kwargs)

    return wrapped
