import logging
from datetime import UTC, datetime, timedelta

from flask import Blueprint, request, jsonify, render_template, abort

from database import db
from sqlalchemy_models import AgentNotification, Agent
from services.notification_service import notification_service
from utils.execution_tracer import log_execution


bp = Blueprint('notifications', __name__)
logger = logging.getLogger(__name__)


@log_execution
def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@bp.route('/api/agents/<int:agent_id>/notifications')
@log_execution
def get_agent_notifications(agent_id: int):
    """Get notifications for a specific agent."""
    try:
        # Verify agent exists
        agent = db.session.get(Agent, agent_id)
        if not agent:
            abort(404, description="Agent not found")
        
        # Get query parameters
        status = request.args.get('status')  # unread, read, dismissed
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100
        
        # Get notifications
        notifications = notification_service.get_agent_notifications(
            agent_id=agent_id,
            status=status,
            limit=limit
        )
        
        # Convert to dictionaries
        notifications_data = [notif.to_dict() for notif in notifications]
        
        return jsonify(notifications_data)
        
    except Exception as e:
        logger.error(f"Error getting agent notifications: {str(e)}")
        return jsonify({'error': 'Failed to load notifications'}), 500


@bp.route('/api/agents/<int:agent_id>/notifications/summary')
@log_execution
def get_agent_notification_summary(agent_id: int):
    """Get notification summary for an agent."""
    try:
        # Verify agent exists
        agent = db.session.get(Agent, agent_id)
        if not agent:
            abort(404, description="Agent not found")
        
        # Get summary
        summary = notification_service.get_notification_summary(agent_id)
        
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Error getting notification summary: {str(e)}")
        return jsonify({'error': 'Failed to load notification summary'}), 500


@bp.route('/api/agents/<int:agent_id>/notifications/<int:notification_id>/read', methods=['POST'])
@log_execution
def mark_notification_read(agent_id: int, notification_id: int):
    """Mark a specific notification as read."""
    try:
        success = notification_service.mark_notification_as_read(notification_id, agent_id)
        
        if success:
            return jsonify({'status': 'success', 'message': 'Notification marked as read'})
        else:
            return jsonify({'error': 'Notification not found or access denied'}), 404
            
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return jsonify({'error': 'Failed to mark notification as read'}), 500


@bp.route('/api/agents/<int:agent_id>/notifications/<int:notification_id>/dismiss', methods=['POST'])
@log_execution
def dismiss_notification(agent_id: int, notification_id: int):
    """Dismiss a specific notification."""
    try:
        success = notification_service.dismiss_notification(notification_id, agent_id)
        
        if success:
            return jsonify({'status': 'success', 'message': 'Notification dismissed'})
        else:
            return jsonify({'error': 'Notification not found or access denied'}), 404
            
    except Exception as e:
        logger.error(f"Error dismissing notification: {str(e)}")
        return jsonify({'error': 'Failed to dismiss notification'}), 500


@bp.route('/api/agents/<int:agent_id>/notifications/mark-all-read', methods=['POST'])
@log_execution
def mark_all_notifications_read(agent_id: int):
    """Mark all unread notifications as read for an agent."""
    try:
        # Verify agent exists
        agent = db.session.get(Agent, agent_id)
        if not agent:
            abort(404, description="Agent not found")
        
        # Get all unread notifications
        unread_notifications = db.session.query(AgentNotification).filter_by(
            agent_id=agent_id,
            status='unread'
        ).all()
        
        # Mark all as read
        marked_count = 0
        for notification in unread_notifications:
            success = notification_service.mark_notification_as_read(notification.id, agent_id)
            if success:
                marked_count += 1
        
        return jsonify({
            'status': 'success',
            'message': f'Marked {marked_count} notifications as read',
            'marked_count': marked_count
        })
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        return jsonify({'error': 'Failed to mark notifications as read'}), 500


@bp.route('/api/agents/<int:agent_id>/notifications/cleanup', methods=['POST'])
@log_execution
def cleanup_agent_notifications(agent_id: int):
    """Clean up old read/dismissed notifications for an agent."""
    try:
        # Verify agent exists
        agent = db.session.get(Agent, agent_id)
        if not agent:
            abort(404, description="Agent not found")
        
        # Get parameters
        days_old = min(int(request.json.get('days_old', 30)), 90)  # Max 90 days
        
        # Delete old read/dismissed notifications
        cutoff_date = _utcnow_naive() - timedelta(days=days_old)
        
        old_notifications = db.session.query(AgentNotification).filter(
            AgentNotification.agent_id == agent_id,
            AgentNotification.created_at < cutoff_date,
            AgentNotification.status.in_(['read', 'dismissed'])
        ).all()
        
        deleted_count = len(old_notifications)
        for notification in old_notifications:
            db.session.delete(notification)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Cleaned up {deleted_count} old notifications',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cleaning up notifications: {str(e)}")
        return jsonify({'error': 'Failed to cleanup notifications'}), 500


@bp.route('/api/notifications/system', methods=['POST'])
@log_execution
def create_system_notification():
    """Create a system notification (admin/internal use)."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['agent_id', 'title', 'message']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create notification
        notification = notification_service.create_system_notification(
            agent_id=data['agent_id'],
            title=data['title'],
            message=data['message'],
            priority=data.get('priority', 'normal'),
            send_email=data.get('send_email', False)
        )
        
        if notification:
            return jsonify({
                'status': 'success',
                'message': 'System notification created',
                'notification_id': notification.id
            })
        else:
            return jsonify({'error': 'Failed to create notification'}), 500
            
    except Exception as e:
        logger.error(f"Error creating system notification: {str(e)}")
        return jsonify({'error': 'Failed to create system notification'}), 500


@bp.route("/api/notifications/inbox")
@log_execution
def notifications_inbox():
    """
    Global match-alert inbox for the PH shell bell.
    Optional ?agent_id= — default: most recent notifications across agents.
    """
    try:
        agent_id = request.args.get("agent_id", type=int)
        limit = min(int(request.args.get("limit", 15)), 50)
        status = request.args.get("status", "unread")

        q = db.session.query(AgentNotification).order_by(
            AgentNotification.created_at.desc()
        )
        if agent_id:
            q = q.filter(AgentNotification.agent_id == agent_id)
        if status and status != "all":
            q = q.filter(AgentNotification.status == status)

        rows = q.limit(limit).all()
        unread_q = db.session.query(AgentNotification).filter(
            AgentNotification.status == "unread"
        )
        if agent_id:
            unread_q = unread_q.filter(AgentNotification.agent_id == agent_id)
        unread_count = unread_q.count()

        # Default agent for mark-read actions: first agent with unread, else first agent
        default_agent_id = agent_id
        if not default_agent_id and rows:
            default_agent_id = rows[0].agent_id
        if not default_agent_id:
            first = db.session.query(Agent).order_by(Agent.id.asc()).first()
            default_agent_id = first.id if first else None

        return jsonify(
            {
                "unread_count": unread_count,
                "default_agent_id": default_agent_id,
                "notifications": [n.to_dict() for n in rows],
            }
        )
    except Exception as e:
        logger.error("Error loading notification inbox: %s", e)
        return jsonify({"error": "Failed to load inbox", "unread_count": 0, "notifications": []}), 500


@bp.route('/admin/notifications')
@log_execution
def admin_notifications_dashboard():
    """Admin dashboard for managing notifications."""
    try:
        # Get notification statistics
        # Recent notifications (last 7 days)
        since = _utcnow_naive() - timedelta(days=7)
        recent_notifications = db.session.query(AgentNotification).filter(
            AgentNotification.created_at >= since
        ).all()
        
        # Group by agent
        agent_stats = {}
        for notif in recent_notifications:
            if notif.agent_id not in agent_stats:
                agent = db.session.get(Agent, notif.agent_id)
                agent_stats[notif.agent_id] = {
                    'agent_name': agent.name if agent else f'Agent {notif.agent_id}',
                    'total': 0,
                    'unread': 0,
                    'high_priority': 0
                }
            
            agent_stats[notif.agent_id]['total'] += 1
            if notif.status == 'unread':
                agent_stats[notif.agent_id]['unread'] += 1
            if notif.priority == 'high':
                agent_stats[notif.agent_id]['high_priority'] += 1
        
        # Overall statistics
        total_notifications = len(recent_notifications)
        unread_count = len([n for n in recent_notifications if n.status == 'unread'])
        high_priority_count = len([n for n in recent_notifications if n.priority == 'high'])
        
        stats = {
            'total_notifications_7d': total_notifications,
            'unread_count': unread_count,
            'high_priority_count': high_priority_count,
            'agent_stats': list(agent_stats.values())
        }
        
        return render_template('admin_notifications.html', stats=stats)
        
    except Exception as e:
        logger.error(f"Error loading admin notifications dashboard: {str(e)}")
        abort(500)


@bp.route('/api/admin/notifications/broadcast', methods=['POST'])
@log_execution
def broadcast_system_notification():
    """Broadcast a system notification to multiple agents."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['title', 'message']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Get target agents
        agent_ids = data.get('agent_ids', [])
        if not agent_ids:
            # Get all active agents
            agents = db.session.query(Agent).filter_by(status='active').all()
            agent_ids = [agent.id for agent in agents]
        
        # Create notifications for each agent
        created_count = 0
        for agent_id in agent_ids:
            notification = notification_service.create_system_notification(
                agent_id=agent_id,
                title=data['title'],
                message=data['message'],
                priority=data.get('priority', 'normal'),
                send_email=data.get('send_email', False)
            )
            
            if notification:
                created_count += 1
        
        return jsonify({
            'status': 'success',
            'message': f'Broadcast notification sent to {created_count} agents',
            'created_count': created_count
        })
        
    except Exception as e:
        logger.error(f"Error broadcasting system notification: {str(e)}")
        return jsonify({'error': 'Failed to broadcast notification'}), 500
