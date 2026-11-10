import os

# Import the Flask application factory for the WSGI server.
from app import create_app

# Construct the application using the selected environment configuration.
app = create_app(os.getenv("APP_ENV", "development"))