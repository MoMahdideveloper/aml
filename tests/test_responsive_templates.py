import pytest


@pytest.mark.skip(
    reason="Unwritten scaffold: responsive template behavior has no test body "
    "yet. Was a bare `assert False`, which reported as a real failure in every "
    "run. Real responsive coverage lives in test_accessibility_responsive.py."
)
def test_responsive_templates():
    pass
