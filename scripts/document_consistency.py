"""Read-only DB/storage consistency report (IDs and counts only)."""

from __future__ import annotations

import argparse
import os
import sys

# run from repo root with FLASK_APP
sys.path.insert(0, os.getcwd())


def main():
    parser = argparse.ArgumentParser(description="Document storage consistency (read-only)")
    parser.add_argument("--repair", action="store_true", help="reserved — not implemented")
    args = parser.parse_args()
    if args.repair:
        print("Repair mode requires separate explicit approval — refusing.")
        return 2

    from app import create_app
    from database import db
    from services.document_storage import get_document_storage
    from sqlalchemy_models import Document

    app = create_app()
    with app.app_context():
        store = get_document_storage()
        missing = 0
        ok = 0
        for doc in Document.query.limit(5000).all():
            area = "archived" if doc.status == "archived" else (
                "quarantine" if doc.status == "quarantined" else "available"
            )
            if store.exists(doc.storage_key, area=area) or store.exists(doc.storage_key):
                ok += 1
            else:
                missing += 1
                print(f"MISSING document_id={doc.id} status={doc.status}")
        print(f"checked_ok={ok} missing={missing}")
    return 0 if missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
