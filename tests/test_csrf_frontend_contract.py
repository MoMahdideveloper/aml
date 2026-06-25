import os


def test_agents_page_delete_flow_includes_csrf_header(client, db_setup):
    response = client.get("/agents")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "X-CSRFToken" in html
    assert "credentials: 'same-origin'" in html


def test_property_details_template_ai_fetch_includes_csrf_header():
    template_path = os.path.join("templates", "property_details.html")
    with open(template_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    assert "X-CSRFToken" in content
    assert "credentials: \"same-origin\"" in content
    assert "X-Requested-With" in content


def test_shared_ai_autofill_fetch_includes_csrf_header():
    js_path = os.path.join("static", "js", "main.js")
    with open(js_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    assert "headers['X-CSRFToken'] = csrfToken;" in content
    assert "credentials: 'same-origin'" in content
    assert "'X-Requested-With': 'XMLHttpRequest'" in content
