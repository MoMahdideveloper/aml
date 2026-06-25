from app import create_app
from flask import url_for

app = create_app()

# Simulate the exact condition from the template:
# href="{{ url_for('auth.logout') if current_user else url_for('admin_environment.admin_logout') }}"
# For unauthenticated users, current_user is falsy, so we test the else branch

with app.app_context():
    # Try to generate the URL that's failing
    try:
        url = url_for('admin_environment.admin_logout')
        print(f"SUCCESS: url_for('admin_environment.admin_logout') = {url}")
    except Exception as e:
        print(f"ERROR: url_for('admin_environment.admin_logout') failed with: {e}")
        print(f"Error type: {type(e).__name__}")

    # Also test the auth.logout for comparison
    try:
        url = url_for('auth.logout')
        print(f"SUCCESS: url_for('auth.logout') = {url}")
    except Exception as e:
        print(f"ERROR: url_for('auth.logout') failed with: {e}")

    # Let's also check what endpoints are actually available
    print("\nAvailable endpoints containing 'admin_environment' or 'auth':")
    for rule in app.url_map.iter_rules():
        if 'admin_environment' in rule.endpoint or 'auth' in rule.endpoint:
            print(f"  {rule.endpoint} -> {rule.rule}")