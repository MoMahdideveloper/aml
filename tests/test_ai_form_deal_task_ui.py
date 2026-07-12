"""Deal and task pages include AI form assist panel contract."""


def test_deals_page_includes_panel_and_script(db_setup, app, monkeypatch):
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")
    monkeypatch.setenv("ENABLE_AI_FORM_ASSIST", "1")
    client = app.test_client()
    r = client.get("/deals")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "data-ai-form-assist" in html
    assert 'data-form-name="deal"' in html
    assert "ai-form-assist.js" in html
    assert 'name="offer_amount"' in html
    assert 'name="property_id"' in html
    assert 'name="customer_id"' in html


def test_tasks_page_includes_panel_and_script(db_setup, app, monkeypatch):
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")
    monkeypatch.setenv("ENABLE_AI_FORM_ASSIST", "1")
    client = app.test_client()
    r = client.get("/tasks")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "data-ai-form-assist" in html
    assert 'data-form-name="task"' in html
    assert "ai-form-assist.js" in html
    assert 'name="title"' in html
    assert 'name="priority"' in html
    assert 'name="due_date"' in html
