from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)
    email = db.Column(db.String, nullable=False, unique=True)
    password_hash = db.Column(db.String, nullable=False)
    role = db.Column(
        db.String,
        nullable=False,
        default="user",
        server_default="user",
    )

    recipes = db.relationship("Recipe", back_populates="user", order_by="Recipe.id")


class Recipe(db.Model):
    __tablename__ = "recipes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    cook_time_minutes = db.Column(db.Integer, nullable=False)
    prep_time_minutes = db.Column(db.Integer, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    notes = db.Column(db.Text, nullable=True)

    user = db.relationship("User", back_populates="recipes")
