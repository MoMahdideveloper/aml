"""Script to create all new database tables."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database import db

with app.app_context():
    db.create_all()
    print("All tables created successfully")
