from flask import Blueprint, jsonify, request

from app.extensions import cache, db
from app.models import Recipe, User
from app.routes.auth import require_auth
from app.services.recipe_service import (
    get_recipe_by_id,
    get_recipe_count_info,
)

recipes_bp = Blueprint("recipes", __name__)


def recipe_json(recipe):
    return {
        "id": recipe.id,
        "title": recipe.title,
        "ingredients": recipe.ingredients,
        "cook_time_minutes": recipe.cook_time_minutes,
        "prep_time_minutes": recipe.prep_time_minutes,
        "user_id": recipe.user_id,
        "notes": recipe.notes,
    }


def invalidate_recipe_list(user_id):
    cache.delete(f"recipes:user:{user_id}")


@recipes_bp.get("/", strict_slashes=False)
@require_auth
@cache.cached(
    timeout=10,
    make_cache_key=lambda payload: f"recipes:user:{payload['id']}",
)
def list_recipes(payload):
    user = db.session.get(User, payload["id"])
    if user is None:
        return jsonify([]), 200
    recipes = [recipe_json(row) for row in user.recipes]
    return jsonify(recipes), 200


@recipes_bp.post("/", strict_slashes=False)
@require_auth
def create_recipe(payload):
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    ingredients = data.get("ingredients")
    cook_time_minutes = data.get("cook_time_minutes")
    notes = data.get("notes")

    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "title is required"}), 400
    if not isinstance(ingredients, str) or not ingredients.strip():
        return jsonify({"error": "ingredients are required"}), 400
    if not isinstance(cook_time_minutes, int):
        return jsonify({"error": "cook_time_minutes must be an integer"}), 400
    if notes is not None and not isinstance(notes, str):
        return jsonify({"error": "notes must be a string"}), 400

    recipe = Recipe(
        title=title.strip(),
        ingredients=ingredients.strip(),
        cook_time_minutes=cook_time_minutes,
        notes=notes.strip() if notes else None,
        user_id=payload["id"],
    )
    db.session.add(recipe)
    db.session.commit()
    invalidate_recipe_list(payload["id"])
    return jsonify(recipe_json(recipe)), 201


@recipes_bp.get("/count")
@require_auth
def recipe_count(payload):
    count = get_recipe_count_info()
    return jsonify({"count": count}), 200


@recipes_bp.get("/<int:recipe_id>")
@require_auth
def get_recipe(payload, recipe_id):
    recipe = get_recipe_by_id(recipe_id)
    if recipe is None:
        return jsonify({"error": "recipe not found"}), 404
    if recipe.user_id != payload["id"]:
        return jsonify({"error": "forbidden"}), 403
    return jsonify(recipe_json(recipe)), 200


@recipes_bp.put("/<int:recipe_id>")
@require_auth
def update_recipe(payload, recipe_id):
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    ingredients = data.get("ingredients")
    cook_time_minutes = data.get("cook_time_minutes")
    notes = data.get("notes")

    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "title is required"}), 400
    if not isinstance(ingredients, str) or not ingredients.strip():
        return jsonify({"error": "ingredients are required"}), 400
    if not isinstance(cook_time_minutes, int):
        return jsonify({"error": "cook_time_minutes must be an integer"}), 400
    if notes is not None and not isinstance(notes, str):
        return jsonify({"error": "notes must be a string"}), 400

    recipe = get_recipe_by_id(recipe_id)
    if recipe is None:
        return jsonify({"error": "recipe not found"}), 404
    if recipe.user_id != payload["id"]:
        return jsonify({"error": "forbidden"}), 403

    recipe.title = title.strip()
    recipe.ingredients = ingredients.strip()
    recipe.cook_time_minutes = cook_time_minutes
    recipe.notes = notes.strip() if notes else None
    db.session.commit()
    invalidate_recipe_list(payload["id"])
    return jsonify(recipe_json(recipe)), 200


@recipes_bp.delete("/<int:recipe_id>")
@require_auth
def delete_recipe(payload, recipe_id):
    recipe = get_recipe_by_id(recipe_id)
    if recipe is None:
        return jsonify({"error": "recipe not found"}), 404

    user_id = payload["id"]
    if user_id != recipe.user_id and payload["role"] != "admin":
        return jsonify({"error": "forbidden"}), 403

    owner_id = recipe.user_id
    db.session.delete(recipe)
    db.session.commit()
    invalidate_recipe_list(owner_id)
    return jsonify({"message": "recipe deleted"}), 200
