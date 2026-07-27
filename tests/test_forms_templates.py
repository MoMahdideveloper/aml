import pytest


@pytest.mark.skip(
    reason="Unwritten scaffold: form submission against the new templates has "
    "no test body yet. Was a bare `assert False`, which reported as a real "
    "failure in every run."
)
def test_form_submission_with_new_templates():
    pass
