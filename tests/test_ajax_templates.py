import pytest


@pytest.mark.skip(
    reason="Unwritten scaffold: AJAX requests against the new templates have "
    "no test body yet. Was a bare `assert False`, which reported as a real "
    "failure in every run."
)
def test_ajax_requests_with_new_templates():
    pass
