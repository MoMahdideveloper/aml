"""Legacy demo blueprint removed from runtime.

Previously rendered a Stitch export HTML path, which is not part of the
shipped Flask template tree. Use live templates under ``templates/`` and
``tests/test_template_references.py`` for verification.
"""

# Intentionally empty: do not register routes against design-export HTML.
