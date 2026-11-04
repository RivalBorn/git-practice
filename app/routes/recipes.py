import asyncio
import hmac
from functools import wraps

import httpx
from flask import Blueprint, current_app, jsonify, request

from app.extensions import cache, db
from app.routes.auth import require_auth
from app.services.recipe_service import (
    create_recipe as create_recipe_service,
    get_recipe_by_id,
    get_recipe_count_info,
    list_recipes_for_user,
)

recipes_bp = Blueprint("recipes", __name__)


def require_internal_service(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        expected_token = current_app.config.get("INTERNAL_SERVICE_TOKEN")
        if not expected_token:
            current_app.logger.error("INTERNAL_SERVICE_TOKEN is not configured")
            return (
                jsonify(
                    {"error": "internal service authentication is not configured"}
                ),
                503,
            )

        provided_token = request.headers.get("X-Internal-Service-Token", "")
        if not hmac.compare_digest(provided_token, expected_token):
            return jsonify({"error": "internal service authentication required"}), 401

        return view_func(*args, **kwargs)

    return wrapped


def recipe_json(recipe):
    return {
        "id": recipe.id,
        "title": recipe.title,
        "ingredients": recipe.ingredients,
        "cook_time_minutes": recipe.cook_time_minutes,
        "prep_time_minutes": recipe.prep_time_minutes,
        "user_id": recipe.user_id,
        "notes": recipe.notes,
        "tags": [tag.name for tag in recipe.tags],
    }


def invalidate_recipe_list(user_id):
    cache.delete(f"recipes:user:{user_id}")


@recipes_bp.get("/", strict_slashes=False)
@require_internal_service
@require_auth
@cache.cached(
    timeout=10,
    make_cache_key=lambda payload: f"recipes:user:{payload['id']}",
)
def list_recipes(payload):
    recipes = [
        recipe_json(row)
        for row in list_recipes_for_user(payload["id"])
    ]
    return jsonify(recipes), 200


@recipes_bp.post("/", strict_slashes=False)
@require_auth
def create_recipe(payload):
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    ingredients = data.get("ingredients")
    cook_time_minutes = data.get("cook_time_minutes")
    notes = data.get("notes")
    tag_names = data.get("tags")

    if not isinstance(title, str) or not title.strip():
        return jsonify({"error": "title is required"}), 400
    if not isinstance(ingredients, str) or not ingredients.strip():
        return jsonify({"error": "ingredients are required"}), 400
    if not isinstance(cook_time_minutes, int):
        return jsonify({"error": "cook_time_minutes must be an integer"}), 400
    if notes is not None and not isinstance(notes, str):
        return jsonify({"error": "notes must be a string"}), 400
    if tag_names is not None and (
        not isinstance(tag_names, list)
        or any(not isinstance(name, str) for name in tag_names)
    ):
        return jsonify({"error": "tags must be a list of strings"}), 400

    recipe = create_recipe_service(
        title=title.strip(),
        ingredients=ingredients.strip(),
        cook_time_minutes=cook_time_minutes,
        notes=notes.strip() if notes else None,
        user_id=payload["id"],
        tag_names=tag_names,
    )
    invalidate_recipe_list(payload["id"])
    return jsonify(recipe_json(recipe)), 201


@recipes_bp.get("/count")
@require_auth
def recipe_count(payload):
    count = get_recipe_count_info()
    return jsonify({"count": count}), 200


@recipes_bp.get("/async-test")
async def async_recipes_test():
    service_url = current_app.config["SLOW_SERVICE_URL"].rstrip("/")
    timeout = current_app.config["DOWNSTREAM_TIMEOUT_SECONDS"]

    async def fetch_eggs(client):
        try:
            response = await client.get(f"{service_url}/eggs")
            response.raise_for_status()
            return response.json()
        except (httpx.ConnectError, httpx.ConnectTimeout):
            return "SERVICE_DOWN"
        except httpx.TimeoutException:
            return "TIMED_OUT"
        except (httpx.RequestError, httpx.HTTPStatusError):
            return "SERVICE_DOWN"

    async with httpx.AsyncClient(timeout=timeout) as client:
        results = await asyncio.gather(
            fetch_eggs(client),
            fetch_eggs(client),
            fetch_eggs(client),
        )
    return jsonify({"results": results}), 200


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
