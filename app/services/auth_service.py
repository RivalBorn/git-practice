from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from app.data.auth_data import get_user_by_username, insert_user


def register_user(username, email, password):
    password_hash = generate_password_hash(password)
    user_id = insert_user(username, email, password_hash)
    return {
        "id": user_id,
        "username": username,
        "email": email,
        "role": "user",
    }


def authenticate_user(username, password):
    user = get_user_by_username(username)
    if user is None or not check_password_hash(user.password_hash, password):
        return None

    payload = {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(
        payload,
        current_app.config["JWT_SECRET"],
        algorithm="HS256",
    )
