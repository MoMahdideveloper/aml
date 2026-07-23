"""Regression coverage for property update persistence."""

from services.database_service import database_service


def test_property_update_persists_changes(client, app, db_setup):
    """A valid property form update must persist all primary fields."""
    with app.app_context():
        property_obj = database_service.add_property(
            title="Original Title",
            address="Original Address",
            price=100000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=1500,
            description="Original description",
            listing_type="sale",
            status="active",
        )
        property_id = property_obj.id

    response = client.post(
        f"/properties/{property_id}",
        data={
            "title": "Updated Title",
            "address": "Updated Address",
            "property_type": "condo",
            "description": "Updated description",
            "listing_type": "sale",
            "sale_price": "150000",
            "bedrooms": "2",
            "bathrooms": "1",
            "square_feet": "1200",
            "year_built": "2020",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["message"] == "Property updated successfully"
    assert payload["data"]["property"]["title"] == "Updated Title"

    with app.app_context():
        updated = database_service.get_property(property_id)
        assert updated.title == "Updated Title"
        assert updated.address == "Updated Address"
        assert updated.price == 150000
        assert updated.property_type == "condo"
        assert updated.bedrooms == 2
        assert updated.bathrooms == 1
        assert updated.square_feet == 1200
        assert updated.year_built == 2020
