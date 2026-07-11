"""Intelligence admin settings toggles."""

from services.hybrid_search import feature_enabled as hybrid_on
from services.intelligence_settings import get_or_create_settings, is_enabled, update_flags
from services.vocab.service import feature_enabled as vocab_on


def test_defaults_seeded_from_env(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_HYBRID_SEARCH", "0")
    monkeypatch.setenv("ENABLE_VOCAB_ENRICHMENT", "0")
    with app.app_context():
        row = get_or_create_settings()
        assert row.hybrid_search is False
        assert row.vocab_enrichment is False
        assert row.global_search is True
        assert is_enabled("global_search") is True
        assert hybrid_on() is False


def test_update_flags_persists_and_updates_config(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_VOCAB_ENRICHMENT", "0")
    with app.app_context():
        get_or_create_settings()
        update_flags({"vocab_enrichment": True}, by="test", app=app)
        row = get_or_create_settings()
        assert row.vocab_enrichment is True
        assert app.config.get("ENABLE_VOCAB_ENRICHMENT") is True
        # Production path (non-TESTING) would read DB; simulate via is_enabled with TESTING off
        app.config["TESTING"] = False
        try:
            assert is_enabled("vocab_enrichment") is True
            update_flags({"vocab_enrichment": False}, by="test", app=app)
            assert is_enabled("vocab_enrichment") is False
        finally:
            app.config["TESTING"] = True



def test_admin_page_denied_anonymous(client, db_setup, app):
    r = client.get("/admin/intelligence", follow_redirects=False)
    assert r.status_code in (301, 302, 401, 403)


def test_admin_page_and_post(client, db_setup, app):
    with client.session_transaction() as sess:
        sess["admin_authenticated"] = True
        sess["admin_user"] = "admin"
    r = client.get("/admin/intelligence")
    assert r.status_code == 200
    assert b"Intelligence settings" in r.data or b"intelligence" in r.data.lower()
    assert b"embedding coverage" in r.data.lower() or b"Coverage" in r.data
    assert b"Customer NL" in r.data or b"customer_nl" in r.data.lower()

    r2 = client.post(
        "/admin/intelligence",
        data={
            "global_search": "1",
            "hybrid_search": "1",
            "vocab_enrichment": "1",
            "customer_nl_filters": "1",
            # others off (unchecked)
        },
        follow_redirects=True,
    )
    assert r2.status_code == 200
    with app.app_context():
        row = get_or_create_settings()
        assert row.hybrid_search is True
        assert row.vocab_enrichment is True
        assert row.ai_context is False
        assert row.customer_nl_filters is True
        assert app.config.get("ENABLE_HYBRID_SEARCH") is True
        assert app.config.get("ENABLE_CUSTOMER_NL_FILTERS") is True


def test_customer_nl_catalog_default_off(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_CUSTOMER_NL_FILTERS", "0")
    from services.intelligence_settings import FLAG_CATALOG, is_enabled
    from services.customer_query_constraints import feature_enabled as cust_nl

    meta = next(f for f in FLAG_CATALOG if f["key"] == "customer_nl_filters")
    assert meta["default"] is False
    assert meta["env"] == "ENABLE_CUSTOMER_NL_FILTERS"
    with app.app_context():
        assert is_enabled("customer_nl_filters") is False
        assert cust_nl() is False

