"""Vocab admin routes require admin auth."""

from sqlalchemy_models import User


def test_anonymous_admin_vocab_denied(client, db_setup, app):
    r = client.get("/admin/vocab", follow_redirects=False)
    assert r.status_code in (301, 302, 401, 403)


def test_admin_session_can_open_vocab(client, db_setup, app):
    with client.session_transaction() as sess:
        sess["admin_authenticated"] = True
        sess["admin_user"] = "admin"
    r = client.get("/admin/vocab")
    assert r.status_code == 200
    assert b"Vocabulary" in r.data or b"vocabulary" in r.data or b"Terms" in r.data


def test_admin_create_term_post(client, db_setup, app):
    with client.session_transaction() as sess:
        sess["admin_authenticated"] = True
    r = client.post(
        "/admin/vocab",
        data={"action": "create_term", "canonical": "villa", "lang": "en"},
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"villa" in r.data.lower()
