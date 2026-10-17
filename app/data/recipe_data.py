from app.models import Recipe
from app.extensions import db


def get_recipe_count():
    return db.session.query(Recipe.id).count()
