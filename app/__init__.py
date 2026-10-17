import os
from dotenv import load_dotenv
from flask import Blueprint, Flask, jsonify
from sqlalchemy import event

from app.config import DevelopmentConfig, ProductionConfig, TestingConfig
from app.extensions import cache, db, limiter, migrate
from app import models
from app.routes.auth import auth_bp
from app.routes.recipes import recipes_bp

# Read local environment settings during module initialization.
load_dotenv()

# Group the application's HTTP endpoints under one Flask blueprint.
routes = Blueprint("routes", __name__)


# Build and configure a Flask application for the requested environment.
def create_app(env_name="development", config_overrides=None):
    # Make values from a local .env file available to the app factory.
    load_dotenv()

    # Create the Flask application instance.
    app = Flask(__name__)

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
    if config_overrides:
        app.config.update(config_overrides)

    # Require an explicit database location for production deployments.
    if env_name == "production" and not app.config.get("DATABASE"):
        raise RuntimeError("DATABASE_URL must be set for production.")

    # Resolve relative database paths against the repository root.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    database_name = app.config["DATABASE"]
    if not os.path.isabs(database_name):
        database_name = os.path.join(project_root, database_name)
    app.config["DATABASE"] = database_name
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{database_name}"

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
        event.listen(db.engine, "connect", enable_sqlite_foreign_keys)

    # Register the new blueprints while retaining routes until they are moved.
    app.register_blueprint(auth_bp, url_prefix="/")
    app.register_blueprint(recipes_bp, url_prefix="/recipes")
    app.register_blueprint(routes)

    @app.errorhandler(429)
    def rate_limit_exceeded(_error):
        return jsonify({"error": "rate limit exceeded"}), 429

    return app


# Create the ORM tables for local development and tests.
def init_db():
    db.create_all()


@routes.get("/health")
def health():
    # Report that the API process is responding.
    return jsonify({"status": "ok"}), 200


# -------------------------
# Recipe routes
# -------------------------


if __name__ == "__main__":
    # Create the app when this module is run directly.
    app = create_app()
    # Start Flask's built-in development server.
    app.run(debug=True)