"""Agent page includes AI form assist panel contract."""


def test_agents_page_includes_panel_and_script(db_setup, app, monkeypatch):
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")
    monkeypatch.setenv("ENABLE_AI_FORM_ASSIST", "1")
    client = app.test_client()
    r = client.get("/agents")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "data-ai-form-assist" in html
    assert 'data-form-name="agent"' in html
    assert "ai-form-assist.js" in html
    assert 'name="name"' in html
    assert 'name="specialization"' in html
    assert 'name="bio"' in html
