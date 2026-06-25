import os
# Remove DATABASE_URL if set to use default file-based database
if 'DATABASE_URL' in os.environ:
    del os.environ['DATABASE_URL']
from app import app
from database import db
with app.app_context():
    db.create_all()
app.run(host='0.0.0.0', port=5003, debug=False, use_reloader=False)