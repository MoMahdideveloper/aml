import os
import json
from flask import Flask
from database import db
from sqlalchemy_models import *

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///demo.db")

with app.app_context():
    try:
        from services.gemini_service import chat_with_agentic_rag
        print("Starting test...")
        history = []
        response = chat_with_agentic_rag("Find me 2 bed properties over 120 meters", history)
        print("Response:", response)
    except Exception as e:
        print("Fatal error:", e)
