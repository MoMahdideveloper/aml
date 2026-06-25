import os
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['ENABLE_CSRF'] = '0'
os.environ['SESSION_SECRET'] = 'testsecret'
from app import app
app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
