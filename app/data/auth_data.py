from app.extensions import db
from app.models import User


def get_user_by_username(username):
    return User.query.filter_by(username=username).first()


def insert_user(username, email, password_hash):
    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        role="user",
    )
    db.session.add(user)
    db.session.commit()
    return user.id
