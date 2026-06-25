import pytest
from sqlalchemy import inspect
from sqlalchemy_models import AnalysisTemplate, AnalysisReport, db

def test_analysis_template_creation(app, db_setup):
    """Test creating an AnalysisTemplate instance."""
    with app.app_context():
        template = AnalysisTemplate(
            name="Code Quality Analysis",
            description="Analyzes code quality metrics",
            analysis_type="code_quality",
            configuration='{"check_style": true, "check_complexity": true}',
            is_active=True
        )
        db.session.add(template)
        db.session.commit()

        assert template.id is not None
        assert template.name == "Code Quality Analysis"
        assert template.description == "Analyzes code quality metrics"
        assert template.analysis_type == "code_quality"
        assert template.configuration == '{"check_style": true, "check_complexity": true}'
        assert template.is_active is True
        assert template.created_at is not None
        assert template.updated_at is not None

def test_analysis_template_to_dict(app, db_setup):
    """Test the to_dict method of AnalysisTemplate."""
    with app.app_context():
        template = AnalysisTemplate(
            name="Architecture Analysis",
            description="Analyzes project architecture",
            analysis_type="architecture",
            configuration='{"check_layers": true, "check_dependencies": true}',
            is_active=False
        )
        db.session.add(template)
        db.session.commit()

        result = template.to_dict()
        assert result["id"] == template.id
        assert result["name"] == "Architecture Analysis"
        assert result["description"] == "Analyzes project architecture"
        assert result["analysis_type"] == "architecture"
        assert result["configuration"] == {"check_layers": True, "check_dependencies": True}
        assert result["is_active"] is False
        assert "created_at" in result
        assert "updated_at" in result

def test_analysis_template_relationship(app, db_setup):
    """Test the relationship between AnalysisTemplate and AnalysisReport."""
    with app.app_context():
        template = AnalysisTemplate(
            name="Security Analysis",
            description="Security vulnerability scan",
            analysis_type="security",
            configuration='{"scan_dependencies": true}',
            is_active=True
        )
        db.session.add(template)
        db.session.flush()  # Get the ID without committing

        report = AnalysisReport(template_id=template.id)
        db.session.add(report)
        db.session.commit()

        # Check that the template has the report in its reports collection
        assert len(template.reports) == 1
        assert template.reports[0].id == report.id
        # Check that the report has the correct template
        assert report.template.id == template.id
        assert report.template.name == "Security Analysis"