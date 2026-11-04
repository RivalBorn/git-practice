from app.extensions import db


recipe_tags = db.Table(
    "recipe_tags",
    db.Column("recipe_id", db.Integer, db.ForeignKey("recipes.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)


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
    tags = db.relationship("Tag", secondary=recipe_tags, back_populates="recipes")


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=True)

    recipes = db.relationship("Recipe", secondary=recipe_tags, back_populates="tags")
