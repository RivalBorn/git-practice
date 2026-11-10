import os
from dotenv import load_dotenv
from flask import Flask, jsonify
from sqlalchemy import event

from app.config import DevelopmentConfig, ProductionConfig, TestingConfig
from app.extensions import cache, db, limiter, migrate
from app import models
from app.routes.auth import auth_bp
from app.routes.gateway import gateway_bp
from app.routes.health import health_bp
from app.routes.recipes import recipes_bp

# Read local environment settings during module initialization.
load_dotenv()

# Build and configure a Flask application for the requested environment.
def create_app(env_name="development", config_overrides=None, service="all"):
    # Make values from a local .env file available to the app factory.
    load_dotenv()

    # Create the Flask application instance.
    app = Flask(__name__)
    if service not in {"all", "gateway", "users", "recipes"}:
        raise ValueError(f"Unsupported service: {service}")

    # Map supported environment names to their settings classes.
    config_map = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }

    # Use development settings when the requested name is unrecognized.
    config_class = config_map.get(env_name, DevelopmentConfig)
    # Copy the selected class settings onto the Flask application.
    app.config.from_object(config_class)
    app.config.setdefault(
        "USERS_SERVICE_URL",
        os.getenv("USERS_SERVICE_URL", "http://127.0.0.1:5001"),
    )
    app.config.setdefault(
        "RECIPES_SERVICE_URL",
        os.getenv("RECIPES_SERVICE_URL", "http://127.0.0.1:5002"),
    )
    app.config.setdefault(
        "SLOW_SERVICE_URL",
        os.getenv("SLOW_SERVICE_URL", "http://127.0.0.1:5001"),
    )
    app.config.setdefault(
        "DOWNSTREAM_TIMEOUT_SECONDS",
        float(os.getenv("DOWNSTREAM_TIMEOUT_SECONDS", "0.6")),
    )
    if config_overrides:
        app.config.update(config_overrides)

    # Require an explicit database URL for production deployments.
    if env_name == "production" and not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL must be set for production.")

    # Load the signing key used to create and verify JWTs.
    app.config["JWT_SECRET"] = os.getenv("JWT_SECRET") or app.config.get("JWT_SECRET")

    # Refuse to start when token signing would have no configured key.
    if not app.config["JWT_SECRET"]:
        raise RuntimeError("JWT_SECRET is not set in the environment.")

    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    limiter.init_app(app)

    def enable_sqlite_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    with app.app_context():
        if db.engine.dialect.name == "sqlite":
            event.listen(db.engine, "connect", enable_sqlite_foreign_keys)

    if service == "all":
        app.register_blueprint(auth_bp, url_prefix="/")
        app.register_blueprint(recipes_bp, url_prefix="/recipes")
    elif service == "gateway":
        app.register_blueprint(gateway_bp)
    elif service == "users":
        app.register_blueprint(auth_bp, url_prefix="/")
    else:
        app.register_blueprint(recipes_bp, url_prefix="/recipes")

    # Gateway has its own health response; other service modes use the shared one.
    if service != "gateway":
        app.register_blueprint(health_bp)

    @app.errorhandler(429)
    def rate_limit_exceeded(_error):
        return jsonify({"error": "rate limit exceeded"}), 429

    return app


# Create the ORM tables for local development and tests.
def init_db():
    db.create_all()


# -------------------------
# Recipe routes
# -------------------------


if __name__ == "__main__":
    # Create the app when this module is run directly.
    app = create_app()
    # Start Flask's built-in development server.
    app.run(debug=True)