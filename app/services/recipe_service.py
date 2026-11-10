from app.extensions import db
from app.models import Recipe, Tag
from app.data.recipe_data import get_recipe_count


def get_or_create_tags(tag_names):
    tags = []
    seen_names = set()

    for name in tag_names or []:
        normalized_name = name.strip()
        if not normalized_name or normalized_name in seen_names:
            continue
        seen_names.add(normalized_name)

        tag = Tag.query.filter_by(name=normalized_name).first()
        if tag is None:
            tag = Tag(name=normalized_name)
            db.session.add(tag)
        tags.append(tag)

    return tags


def create_recipe(title, ingredients, cook_time_minutes, user_id, notes=None, tag_names=None):
    recipe = Recipe(
        title=title,
        ingredients=ingredients,
        cook_time_minutes=cook_time_minutes,
        notes=notes,
        user_id=user_id,
        tags=get_or_create_tags(tag_names),
    )
    db.session.add(recipe)
    db.session.commit()
    return recipe


def get_recipe_count_info():
    return get_recipe_count()


def get_recipe_by_id(recipe_id):
    return db.session.get(Recipe, recipe_id)


def list_recipes_for_user(user_id):
    return Recipe.query.filter_by(user_id=user_id).order_by(Recipe.id).all()


def get_recipe_page_for_user(user_id, page, per_page):
    query = Recipe.query.filter_by(user_id=user_id)
    total = query.count()
    recipes = (
        query.order_by(Recipe.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return recipes, total
