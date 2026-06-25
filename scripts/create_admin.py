"""
Create an admin user directly in the database.
Usage: python scripts/create_admin.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from database import db
from sqlalchemy_models import User


def create_admin():
    # ── Admin credentials ──
    ADMIN_USERNAME = "admin"
    ADMIN_EMAIL = "admin@crm.local"
    ADMIN_PASSWORD = "Admin@2026"
    ADMIN_FULL_NAME = "System Administrator"
    ADMIN_PHONE = "09120000000"

    app = create_app()
    with app.app_context():
        # Check if admin already exists
        existing = User.query.filter_by(username=ADMIN_USERNAME).first()
        if existing:
            print(f"Admin user '{ADMIN_USERNAME}' already exists (id={existing.id}, role={existing.role}).")
            if existing.role != "admin":
                existing.role = "admin"
                db.session.commit()
                print(f"  → Role upgraded to 'admin'.")
            return

        user = User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            full_name=ADMIN_FULL_NAME,
            phone=ADMIN_PHONE,
            role="admin",
        )
        user.set_password(ADMIN_PASSWORD)
        db.session.add(user)
        db.session.commit()

        print(f"✅ Admin user created successfully!")
        print(f"   Username : {ADMIN_USERNAME}")
        print(f"   Email    : {ADMIN_EMAIL}")
        print(f"   Password : {ADMIN_PASSWORD}")
        print(f"   Role     : admin")

        # Save credentials to file
        creds_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "admin_credentials.txt")
        with open(creds_path, "w", encoding="utf-8") as f:
            f.write("=== CRM Admin Credentials ===\n")
            f.write(f"Username : {ADMIN_USERNAME}\n")
            f.write(f"Email    : {ADMIN_EMAIL}\n")
            f.write(f"Password : {ADMIN_PASSWORD}\n")
            f.write(f"Role     : admin\n")
            f.write(f"Login URL: http://127.0.0.1:5000/auth/login\n")
        print(f"\n📄 Credentials saved to: {creds_path}")


if __name__ == "__main__":
    create_admin()
