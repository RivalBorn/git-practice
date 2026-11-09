"""Initialize and configure the Tiny Todo Flask application."""

import os

from flask import Flask

from app.extensions import db, migrate
from app import models
from app.routes import todos_bp


class Config:
    """Provide shared application and database configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", SECRET_KEY)
    JWT_LIFETIME_SECONDS = int(os.environ.get("JWT_LIFETIME_SECONDS", "3600"))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///tiny-todo.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    """Configure the application for local development."""

    DEBUG = True


def create_app(config_name="development"):
    """Create the Flask app, initialize extensions, and register routes."""
    app = Flask(__name__)
    configs = {"development": DevelopmentConfig}
    app.config.from_object(configs[config_name])
    db.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(todos_bp, url_prefix="/api")
    return app