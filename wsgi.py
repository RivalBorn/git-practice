# Import the Flask application factory for the WSGI server.
from app import create_app

# Construct the application using its default environment configuration.
app = create_app()