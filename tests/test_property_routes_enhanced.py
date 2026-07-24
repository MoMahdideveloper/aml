"""Live-contract coverage for property detail and deletion routes."""

from database import db
from services.database_service import database_service
from sqlalchemy_models import Property


def _seed_property():
    property_obj = database_service.add_property(
        title="Integration Property",
        address="123 Integration Street",
        price=250000,
        property_type="house",
        bedrooms=3,
        bathrooms=2,
        square_feet=1500,
        description="A property used by route integration tests.",
        listing_type="sale",
        status="active",
    )
    return property_obj.id


def test_property_detail_renders_for_existing_property(client, app, db_setup):
    with app.app_context():
        property_id = _seed_property()

    response = client.get(f"/properties/{property_id}/detail")

    assert response.status_code == 200
    assert b"Integration Property" in response.data
    assert b"123 Integration Street" in response.data


def test_missing_property_routes_redirect_to_dashboard(client, app, db_setup):
    detail_response = client.get("/properties/99999/detail")
    view_response = client.get("/properties/99999")

    assert detail_response.status_code == 302
    assert detail_response.location.endswith("/dashboard")
    assert view_response.status_code == 302
    assert view_response.location.endswith("/dashboard")


def test_property_delete_redirects_and_marks_row_deleted(client, app, db_setup):
    with app.app_context():
        property_id = _seed_property()

    response = client.post(f"/properties/{property_id}/delete")

    assert response.status_code == 302
    assert response.location.endswith("/properties")

    with app.app_context():
        deleted = db.session.get(Property, property_id)
        assert deleted is not None
        assert deleted.status == "archived"


def test_invalid_property_id_returns_not_found(client, app, db_setup):
    response = client.get("/properties/not-an-id/detail")

    assert response.status_code == 404
