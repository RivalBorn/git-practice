from app.extensions import db
from app.models import Recipe
from app.data.recipe_data import get_recipe_count


def get_recipe_count_info():
    return get_recipe_count()


def get_recipe_by_id(recipe_id):
    return db.session.get(Recipe, recipe_id)


def list_recipes_for_user(user_id):
    return Recipe.query.filter_by(user_id=user_id).order_by(Recipe.id).all()
