"""Customer / recommendation pages include AI form assist panel contract."""


def test_customers_page_includes_panel_and_script(db_setup, app, monkeypatch):
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")
    monkeypatch.setenv("ENABLE_AI_FORM_ASSIST", "1")
    client = app.test_client()
    r = client.get("/customers")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "data-ai-form-assist" in html
    assert 'data-form-name="customer"' in html
    assert "ai-form-assist.js" in html
    assert 'name="name"' in html
    assert 'name="budget_max"' in html
    assert 'name="location_preference"' in html


def test_recommendations_page_loads(db_setup, app, monkeypatch):
    """Recommendations always loads script; panel appears when a client is selected."""
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")
    monkeypatch.setenv("ENABLE_AI_FORM_ASSIST", "1")
    client = app.test_client()
    r = client.get("/recommendations")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "ai-form-assist.js" in html
