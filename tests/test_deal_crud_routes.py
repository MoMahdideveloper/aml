"""Tests for the current deal pipeline HTML, JSON, and form routes."""

from services.database_service import database_service


def _seed_deal(app, sample_data) -> int:
    """Create one deal and return only its scalar ID after the session closes."""
    with app.app_context():
        from sqlalchemy_models import Agent

        agent_id = Agent.query.filter_by(email="agent@test.com").one().id
        deal = database_service.add_deal(
            property_id=sample_data["properties"][0]["id"],
            customer_id=sample_data["customers"][0]["id"],
            agent_id=agent_id,
            status="prospecting",
            offer_amount=450000,
        )
        return deal.id


class TestDealCRUDRoutes:
    """Exercise the live form-based deal pipeline and JSON read endpoint."""

    def test_deals_pipeline_page_loads(self, client, app, sample_data):
        _seed_deal(app, sample_data)

        response = client.get("/deals")

        assert response.status_code == 200
        assert b"Prospecting" in response.data

    def test_deal_json_api_success(self, client, app, sample_data):
        deal_id = _seed_deal(app, sample_data)

        response = client.get(f"/api/deals/{deal_id}")

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == deal_id
        assert data["status"] == "prospecting"
        assert data["property_id"] == sample_data["properties"][0]["id"]
        assert data["customer_id"] == sample_data["customers"][0]["id"]
        assert data["property_title"] == "Luxury Villa"
        assert data["customer_name"] == "John Doe"
        assert data["agent_name"] == "Test Agent"

    def test_deal_json_api_not_found(self, client):
        response = client.get("/api/deals/99999")

        assert response.status_code == 404
        assert response.get_json() == {"error": "Deal not found"}

    def test_deal_update_via_post(self, client, app, sample_data):
        deal_id = _seed_deal(app, sample_data)

        response = client.post(
            f"/deals/{deal_id}/update",
            data={"status": "negotiation", "offer_amount": "460000"},
        )

        assert response.status_code == 302
        assert response.location.endswith("/deals")
        updated = client.get(f"/api/deals/{deal_id}").get_json()
        assert updated["status"] == "negotiation"
        assert updated["offer_amount"] == 460000

    def test_deal_note_via_post(self, client, app, sample_data):
        deal_id = _seed_deal(app, sample_data)

        response = client.post(
            f"/deals/{deal_id}/note",
            data={"note": "Call client about the next viewing"},
        )

        assert response.status_code == 302
        assert response.location.endswith("/deals")
        updated = client.get(f"/api/deals/{deal_id}").get_json()
        assert "Call client about the next viewing" in updated["notes"]

    def test_deal_delete_via_post_soft_deletes(self, client, app, sample_data):
        deal_id = _seed_deal(app, sample_data)

        response = client.post(f"/deals/{deal_id}/delete")

        assert response.status_code == 302
        assert response.location.endswith("/deals")
        deleted = client.get(f"/api/deals/{deal_id}")
        assert deleted.status_code == 404
        assert deleted.get_json() == {"error": "Deal not found"}
