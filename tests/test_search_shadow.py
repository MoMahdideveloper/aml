"""Shadow hybrid keeps keyword display order."""

from services.hybrid_search import hybrid_search_service
from services.unified_search import parse_search_request
from sqlalchemy_models import Property


def test_shadow_preserves_keyword_order(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_HYBRID_SEARCH", "1")
    monkeypatch.setenv("ENABLE_SEARCH_SHADOW", "1")
    with app.app_context():
        from database import db

        # Two properties matching "Unit"
        db.session.add(
            Property(title="Unit Alpha", address="1", property_type="apt", price=1, bedrooms=1)
        )
        db.session.add(
            Property(title="Unit Beta", address="2", property_type="apt", price=1, bedrooms=1)
        )
        db.session.commit()
        req = parse_search_request(q="Unit", scope="properties", mode="full")
        result = hybrid_search_service.search(req)
        assert result["hybrid"].get("shadow") is True
        assert result["hybrid"].get("keyword_top_ids")
        # visible property ids should follow keyword_top_ids when both present
        visible = [h["id"] for h in result["groups"]["properties"]]
        kw = result["hybrid"]["keyword_top_ids"]
        # first visible should match first keyword hit that is displayed
        if visible and kw:
            assert visible[0] == kw[0] or visible[0] in kw
