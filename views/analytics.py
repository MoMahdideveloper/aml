from flask import Blueprint, request, jsonify
from sqlalchemy_models import AnalysisTemplate, AnalysisReport, SuggestionItem, AnalysisMetric, db
import json
from datetime import datetime

# Create blueprint
analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/templates', methods=['GET'])
def get_analysis_templates():
    '''Get list of analysis templates'''
    try:
        templates = AnalysisTemplate.query.filter_by(is_active=True).all()
        return jsonify([template.to_dict() for template in templates]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/templates', methods=['POST'])
def create_analysis_template():
    '''Create a new analysis template'''
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['name', 'analysis_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400

        template = AnalysisTemplate(
            name=data['name'],
            description=data.get('description', ''),
            analysis_type=data['analysis_type'],
            configuration=json.dumps(data.get('configuration', {})),
            is_active=data.get('is_active', True)
        )

        db.session.add(template)
        db.session.commit()

        return jsonify(template.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/trigger', methods=['POST'])
def trigger_analysis():
    '''Trigger a new analysis'''
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['template_id', 'name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400

        # Verify template exists
        template = AnalysisTemplate.query.get(data['template_id'])
        if not template:
            return jsonify({'error': 'Template not found'}), 404

        # Create analysis report
        report = AnalysisReport(
            template_id=data['template_id'],
            name=data['name'],
            description=data.get('description', ''),
            status='pending'
        )

        db.session.add(report)
        db.session.commit()

        # TODO: Trigger Celery task for background processing
        # For now, we'll just return the created report

        return jsonify(report.to_dict()), 202
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/reports', methods=['GET'])
def get_analysis_reports():
    '''Get list of analysis reports with filtering and pagination'''
    try:
        # Get query parameters for filtering
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        analysis_type = request.args.get('analysis_type')

        # Build query
        query = AnalysisReport.query

        if status:
            query = query.filter_by(status=status)

        if analysis_type:
            # Join with template to filter by analysis_type
            query = query.join(AnalysisTemplate).filter(
                AnalysisTemplate.analysis_type == analysis_type
            )

        # Paginate results
        reports = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'reports': [report.to_dict() for report in reports.items],
            'total': reports.total,
            'pages': reports.pages,
            'current_page': reports.page
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/reports/<int:report_id>', methods=['GET'])
def get_analysis_report(report_id):
    '''Get detailed report by ID'''
    try:
        report = AnalysisReport.query.get_or_404(report_id)
        return jsonify(report.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/reports/<int:report_id>/status', methods=['GET'])
def get_analysis_report_status(report_id):
    '''Get analysis progress/status'''
    try:
        report = AnalysisReport.query.get_or_404(report_id)
        # For now, return basic status info
        # In a real implementation, this would check Celery task status
        return jsonify({
            'id': report.id,
            'status': report.status,
            'progress': 100 if report.status == 'completed' else
                       50 if report.status == 'processing' else 0,
            'updated_at': report.updated_at.isoformat() if report.updated_at else None
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/suggestions/<int:suggestion_id>', methods=['PUT'])
def update_suggestion(suggestion_id):
    '''Update suggestion status/assignment'''
    try:
        suggestion = SuggestionItem.query.get_or_404(suggestion_id)
        data = request.get_json()

        # Update fields if provided (map API field names to model field names)
        if 'status' in data:
            suggestion.status = data['status']
        if 'assigned_to' in data:
            suggestion.assigned_to = data['assigned_to']
        if 'priority' in data:
            suggestion.priority_score = data['priority']
        if 'implementation_effort' in data:
            suggestion.implementation_complexity = data['implementation_effort']
        if 'estimated_impact' in data:
            # Map estimated_impact to roi_estimate (assuming percentage-like value)
            # Convert qualitative values to numeric approximations if needed
            impact_value = data['estimated_impact']
            if isinstance(impact_value, str):
                # Map qualitative descriptions to numeric values
                impact_mapping = {
                    'low': 10,
                    'medium': 50,
                    'high': 80
                }
                suggestion.roi_estimate = impact_mapping.get(impact_value.lower(), 50)
            else:
                # Assume it's already a numeric value
                suggestion.roi_estimate = float(impact_value)

        suggestion.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(suggestion.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/suggestions', methods=['GET'])
def get_suggestions():
    '''Get list of suggestions with filtering and pagination'''
    try:
        # Get query parameters for filtering
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        priority = request.args.get('priority')
        report_id = request.args.get('report_id', type=int)

        # Build query
        query = SuggestionItem.query

        if status:
            query = query.filter_by(status=status)

        if priority:
            # Filter by priority_score (since API uses 'priority' but model uses 'priority_score')
            try:
                priority_value = int(priority)
                query = query.filter_by(priority_score=priority_value)
            except ValueError:
                # If it's not an integer, ignore the filter or handle appropriately
                pass

        if report_id:
            query = query.filter_by(report_id=report_id)

        # Paginate results
        suggestions = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'suggestions': [suggestion.to_dict() for suggestion in suggestions.items],
            'total': suggestions.total,
            'pages': suggestions.pages,
            'current_page': suggestions.page
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/export/<int:report_id>', methods=['GET'])
def export_analysis_report(report_id):
    '''Export report in multiple formats'''
    try:
        report = AnalysisReport.query.get_or_404(report_id)
        format_type = request.args.get('format', 'pdf').lower()

        # TODO: Implement actual export functionality using export_service
        # For now, return placeholder or not implemented

        if format_type == 'pdf':
            return jsonify({
                'message': 'PDF export not yet implemented',
                'report_id': report.id,
                'format': 'pdf'
            }), 501
        elif format_type == 'excel':
            return jsonify({
                'message': 'Excel export not yet implemented',
                'report_id': report.id,
                'format': 'excel'
            }), 501
        elif format_type == 'csv':
            return jsonify({
                'message': 'CSV export not yet implemented',
                'report_id': report.id,
                'format': 'csv'
            }), 501
        else:
            return jsonify({'error': 'Unsupported format'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500