import httpx
from flask import Blueprint, Response, current_app, jsonify, request

from app.routes.auth import require_auth

gateway_bp = Blueprint("gateway", __name__)

_HOP_BY_HOP_HEADERS = {
    "connection",
    "content-length",
    "host",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def _service_url(service):
    config_key = f"{service.upper()}_SERVICE_URL"
    return current_app.config[config_key].rstrip("/")


def _forward(service, path):
    url = f"{_service_url(service)}/{path.lstrip('/')}"
    if request.query_string:
        url = f"{url}?{request.query_string.decode('latin-1')}"

    headers = {
        name: value
        for name, value in request.headers.items()
        if name.lower() not in _HOP_BY_HOP_HEADERS
    }
    if service == "recipes":
        internal_token = current_app.config.get("INTERNAL_SERVICE_TOKEN")
        if not internal_token:
            current_app.logger.error("INTERNAL_SERVICE_TOKEN is not configured")
            return (
                jsonify(
                    {"error": "internal service authentication is not configured"}
                ),
                503,
            )
        headers["X-Internal-Service-Token"] = internal_token

    try:
        downstream = httpx.request(
            request.method,
            url,
            headers=headers,
            content=request.get_data(),
            timeout=current_app.config["DOWNSTREAM_TIMEOUT_SECONDS"],
        )
    except httpx.TimeoutException:
        current_app.logger.warning("Timed out calling the %s service", service)
        return jsonify({"error": "downstream timeout", "service": service}), 504
    except httpx.RequestError:
        current_app.logger.exception("Unable to reach the %s service", service)
        return jsonify({"error": "downstream unavailable", "service": service}), 503

    response_headers = [
        (name, value)
        for name, value in downstream.headers.multi_items()
        if name.lower() not in _HOP_BY_HOP_HEADERS
    ]
    return Response(
        downstream.content,
        status=downstream.status_code,
        headers=response_headers,
    )


@require_auth
def _forward_authenticated(_payload, service, path):
    return _forward(service, path)


def _get_dashboard_component(service, path, authorization):
    headers = {"Authorization": authorization}
    if service == "recipes":
        internal_token = current_app.config.get("INTERNAL_SERVICE_TOKEN")
        if not internal_token:
            current_app.logger.error("INTERNAL_SERVICE_TOKEN is not configured")
            return None, "misconfigured"
        headers["X-Internal-Service-Token"] = internal_token

    try:
        response = httpx.get(
            f"{_service_url(service)}/{path}",
            headers=headers,
            timeout=current_app.config["DOWNSTREAM_TIMEOUT_SECONDS"],
        )
    except httpx.TimeoutException:
        current_app.logger.warning("Timed out calling the %s service", service)
        return None, "timeout"
    except httpx.RequestError:
        current_app.logger.exception("Unable to reach the %s service", service)
        return None, "unavailable"

    if response.status_code != 200:
        return None, f"http_{response.status_code}"

    try:
        return response.json(), None
    except ValueError:
        current_app.logger.error(
            "The %s service returned invalid JSON for the dashboard", service
        )
        return None, "invalid_response"


def _forward_user_path(path):
    if path in {"register", "login"}:
        return _forward("users", path)
    return _forward_authenticated("users", path)


@gateway_bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "gateway"}), 200


@gateway_bp.get("/me")
@require_auth
def me(_payload):
    authorization = request.headers.get("Authorization", "")
    user, user_error = _get_dashboard_component(
        "users",
        "me",
        authorization,
    )
    if user_error is None:
        user_status = "ok"
    elif user_error == "timeout":
        user_status = "timeout"
    elif user_error in {"http_401", "http_403"}:
        user_status = "auth_failed"
    else:
        user_status = "unavailable"

    recipes, recipes_error = _get_dashboard_component(
        "recipes",
        "recipes",
        authorization,
    )
    if recipes_error is None:
        recipes_status = "ok"
    elif recipes_error == "timeout":
        recipes_status = "timeout"
    elif recipes_error in {"http_401", "http_403"}:
        recipes_status = "auth_failed"
    else:
        recipes_status = "unavailable"

    return jsonify(
        {
            "user": user,
            "user_status": user_status,
            "recipes": recipes,
            "recipes_status": recipes_status,
        }
    ), 200


@gateway_bp.get("/health/dependencies")
def dependency_health():
    services = {}
    for service in ("users", "recipes"):
        try:
            response = httpx.get(
                f"{_service_url(service)}/health",
                timeout=current_app.config["DOWNSTREAM_TIMEOUT_SECONDS"],
            )
            if response.status_code == 200:
                services[service] = {"status": "ok"}
            else:
                services[service] = {
                    "status": "unavailable",
                    "http_status": response.status_code,
                }
        except httpx.TimeoutException:
            services[service] = {"status": "unavailable", "error": "timeout"}
        except httpx.RequestError:
            services[service] = {"status": "unavailable", "error": "connection"}

    partial = any(result["status"] != "ok" for result in services.values())
    return jsonify(
        {
            "status": "partial" if partial else "ok",
            "partial": partial,
            "services": services,
        }
    ), (503 if partial else 200)


@gateway_bp.get("/dashboard")
@require_auth
def dashboard(_payload):
    authorization = request.headers.get("Authorization", "")
    recipes, recipe_error = _get_dashboard_component(
        "recipes",
        "recipes",
        authorization,
    )
    user, user_error = _get_dashboard_component("users", "me", authorization)

    errors = {}
    if recipe_error:
        errors["recipes"] = recipe_error
    if user_error:
        errors["user"] = user_error

    result = {
        "recipes": recipes,
        "user": user,
        "partial": bool(errors),
    }
    if errors:
        result["errors"] = errors

    return jsonify(result), (503 if len(errors) == 2 else 200)


@gateway_bp.route(
    "/",
    defaults={"path": ""},
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@gateway_bp.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def proxy(path):
    if path == "recipes" or path.startswith("recipes/"):
        return _forward_authenticated("recipes", path)
    return _forward_user_path(path)
