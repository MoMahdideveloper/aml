"""Property page includes AI form assist panel contract."""


def test_properties_page_includes_panel_and_script(db_setup, app, monkeypatch):
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")
    monkeypatch.setenv("ENABLE_AI_FORM_ASSIST", "1")
    client = app.test_client()
    r = client.get("/properties")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "data-ai-form-assist" in html
    assert "ai-form-assist.js" in html
    assert "AI form assist" in html
    assert 'name="title"' in html
    assert 'name="sale_price"' in html or 'name="sale_price"' in html
