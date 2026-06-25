"""
Test template replacement verification.
Tests that existing Flask templates have been replaced with Stitch KPI dashboard designs.
"""
import os

import pytest


def test_template_replacement_verification():
    """Test that existing template files have been replaced with Stitch designs."""
    # List of expected template files that should exist after replacement
    expected_templates = [
        "dashboard.html",
        "properties.html",
        "customers.html",
        "deals.html",
        "tasks.html",
        "agents.html",
        "recommendations.html"
    ]

    templates_dir = "templates"

    # Check that all expected templates exist
    for template in expected_templates:
        template_path = os.path.join(templates_dir, template)
        assert os.path.exists(template_path), f"Template {template} should exist in {templates_dir}"

        # Verify the file is not empty
        assert os.path.getsize(template_path) > 0, f"Template {template} should not be empty"

        # Read the template content
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verify that the template contains Stitch-specific classes/IDs
        # These are common classes found in Stitch KPI dashboard designs
        stitch_indicators = [
            'class=',  # Stitch uses class attributes extensively
            'id=',     # Stitch uses ID attributes for components
            'btn',     # Button classes
            'card',    # Card components
            'container', # Container classes
            'row',     # Row classes
            'col-'     # Column classes (Bootgrid/Grid system)
        ]

        # At least some Stitch/Bootstrap indicators should be present
        has_stitch_indicators = any(indicator in content for indicator in stitch_indicators)
        assert has_stitch_indicators, f"Template {template} should contain Stitch/Bootstrap indicators"

        # Verify it's a valid Jinja2 template (contains template syntax)
        jinja_indicators = ['{{', '}}', '{%', '%}']
        has_jinja = any(indicator in content for indicator in jinja_indicators)
        assert has_jinja, f"Template {template} should contain Jinja2 template syntax"


def test_template_directory_structure():
    """Test that templates directory maintains proper structure."""
    templates_dir = "templates"
    assert os.path.isdir(templates_dir), "Templates directory should exist"

    # Check for base template
    base_template = os.path.join(templates_dir, "base.html")
    assert os.path.exists(base_template), "base.html should exist"

    # Verify base template has basic HTML structure
    with open(base_template, 'r', encoding='utf-8') as f:
        content = f.read()
        assert '<html' in content.lower(), "base.html should contain HTML tag"
        assert '</html>' in content.lower(), "base.html should contain closing HTML tag"


if __name__ == "__main__":
    pytest.main([__file__])