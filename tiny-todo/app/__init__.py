import os

from flask import Flask

from app.extensions import db, migrate
from app import models
from app.routes import todos_bp


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///tiny-todo.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    DEBUG = True


def create_app(config_name="development"):
    app = Flask(__name__)
    configs = {"development": DevelopmentConfig}
    app.config.from_object(configs[config_name])
    db.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(todos_bp, url_prefix="/api")
    return app