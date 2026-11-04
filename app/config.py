import os
from dotenv import load_dotenv

load_dotenv()


# Convert common environment-variable spellings into a Python boolean.
def env_bool(name, default: bool):
    # Use the caller's environment-specific value when present.
    value = os.environ.get(name)
    # Preserve the config's chosen default when the variable is unset.
    if value is None:
        return default
    # Treat only the listed strings as enabled; other strings are false.
    return value.lower() in ("1", "true", "yes", "on")


# Shared base for the app's environment-specific settings.
class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 10
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_HEADERS_ENABLED = True
    INTERNAL_SERVICE_TOKEN = os.environ.get("INTERNAL_SERVICE_TOKEN")


# Development defaults to debug mode and a local database file.
class DevelopmentConfig(Config):
    DEBUG = env_bool("DEBUG", True)
    DATABASE = os.environ.get("DATABASE_URL", "recipe-dev.db")


# Tests default to debug-off and can use a separately configured database.
class TestingConfig(Config):
    DEBUG = env_bool("DEBUG", False)
    DATABASE = os.environ.get("TEST_DATABASE_URL", "recipe-test.db")
    RATELIMIT_ENABLED = True


# Production has debug disabled by default and requires an env-provided DB.
class ProductionConfig(Config):
    DEBUG = env_bool("DEBUG", False)
    DATABASE = os.environ.get("DATABASE_URL")
