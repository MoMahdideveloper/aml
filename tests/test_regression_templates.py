import pytest


@pytest.mark.skip(
    reason="Unwritten scaffold: template regression coverage has no test body "
    "yet. Was a bare `assert False`, which reported as a real failure in every "
    "run."
)
def test_regression_templates():
    pass
