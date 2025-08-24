import os
import logging
from flask import Flask
from database import init_db

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Initialize database
db = init_db(app)

# Import routes after app creation to avoid circular imports
from routes import *

if __name__ == '__main__':
    # Note: Database tables are created through Flask-Migrate when needed
    pass
