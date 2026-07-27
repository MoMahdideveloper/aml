import pytest


@pytest.mark.skip(
    reason="Unwritten scaffold: dynamic data injection in the recommendations "
    "template has no test body yet. Was a bare `assert False`, which reported "
    "as a real failure in every run."
)
def test_recommendations_template():
    pass
