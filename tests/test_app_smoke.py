def test_app_imports_and_has_routes(app):
    # App should import and have at least one route registered
    rules = list(app.url_map.iter_rules())
    assert len(rules) > 0


def test_app_context_push(app):
    # Pushing an app context should work without hitting heavy services
    with app.app_context():
        assert True
