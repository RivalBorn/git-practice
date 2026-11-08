from app.extensions import db


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", back_populates="tasks")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.String(20), nullable=False, default="user", server_default="user"
    )
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    tasks = db.relationship("Task", back_populates="user")