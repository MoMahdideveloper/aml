import json
import logging
from datetime import UTC, datetime, timedelta
from typing import List, Dict, Optional, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import os

from database import db
from sqlalchemy_models import AgentNotification, Agent, PropertyMatch, Property, Customer
from utils.execution_tracer import log_execution


@log_execution
def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class NotificationService:
    """
    Service for managing agent notifications and high-priority alerts.
    
    Handles:
    - Notification creation and management
    - Email alerts for high-priority matches
    - Notification digests and summaries
    - Read/unread status tracking
    """
    
    def __init__(self):
        self.logger = logging.getLogger("services.notification_service")
        
        # Email configuration
        self.email_enabled = os.environ.get('EMAIL_NOTIFICATIONS_ENABLED', 'false').lower() == 'true'
        self.smtp_server = os.environ.get('SMTP_SERVER', 'localhost')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_username = os.environ.get('SMTP_USERNAME', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.smtp_use_tls = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
        self.from_email = os.environ.get('FROM_EMAIL', 'noreply@realestate-crm.com')
        
        self.high_priority_threshold = 0.85
    
    @log_execution
    def create_property_match_notification(self, 
                                         agent_id: int, 
                                         property_match: PropertyMatch,
                                         send_email: bool = True) -> Optional[AgentNotification]:
        """
        Create a notification for an agent about a property match.
        
        Args:
            agent_id: ID of the agent to notify
            property_match: PropertyMatch object
            send_email: Whether to send email notification for high-priority matches
            
        Returns:
            Created AgentNotification object or None if failed
        """
        try:
            # Load related data
            agent = db.session.get(Agent, agent_id)
            property_obj = db.session.get(Property, property_match.property_id)
            customer = db.session.get(Customer, property_match.customer_id)
            
            if not all([agent, property_obj, customer]):
                self.logger.error(f"Missing data for notification: agent={bool(agent)}, property={bool(property_obj)}, customer={bool(customer)}")
                return None
            
            # Create notification content
            score_pct = int(property_match.match_score * 100)
            title = f"New Property Match ({score_pct}%)"
            
            # Parse match reasons
            try:
                reasons = json.loads(property_match.match_reasons) if property_match.match_reasons else []
            except json.JSONDecodeError:
                reasons = [property_match.match_reasons] if property_match.match_reasons else []
            
            reasons_text = ", ".join(reasons[:3]) if reasons else "AI analysis"
            
            message = (
                f"Customer {customer.name} is a {score_pct}% match for your property at {property_obj.address}. "
                f"Match factors: {reasons_text}. "
                f"Customer budget: ${customer.budget_min:,.0f}-${customer.budget_max:,.0f}. "
                f"Property price: ${property_obj.price:,.0f}."
            )
            
            # Determine priority
            priority = 'high' if property_match.match_score >= self.high_priority_threshold else 'normal'
            
            # Create notification
            notification = AgentNotification(
                agent_id=agent_id,
                property_match_id=property_match.id,
                title=title,
                message=message,
                notification_type='property_match',
                priority=priority
            )
            
            db.session.add(notification)
            db.session.commit()
            
            self.logger.info(f"Created notification {notification.id} for agent {agent_id}")
            
            # Send email for high-priority matches
            if send_email and priority == 'high' and self.email_enabled:
                self._send_high_priority_email(agent, notification, property_match, property_obj, customer)
            
            return notification
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error creating property match notification: {str(e)}")
            return None
    
    @log_execution
    def create_system_notification(self, 
                                 agent_id: int,
                                 title: str,
                                 message: str,
                                 priority: str = 'normal',
                                 send_email: bool = False) -> Optional[AgentNotification]:
        """
        Create a system notification for an agent.
        
        Args:
            agent_id: ID of the agent to notify
            title: Notification title
            message: Notification message
            priority: Priority level (low, normal, high, urgent)
            send_email: Whether to send email notification
            
        Returns:
            Created AgentNotification object or None if failed
        """
        try:
            notification = AgentNotification(
                agent_id=agent_id,
                title=title,
                message=message,
                notification_type='system',
                priority=priority
            )
            
            db.session.add(notification)
            db.session.commit()
            
            self.logger.info(f"Created system notification {notification.id} for agent {agent_id}")
            
            # Send email if requested and enabled
            if send_email and self.email_enabled:
                agent = db.session.get(Agent, agent_id)
                if agent:
                    self._send_system_notification_email(agent, notification)
            
            return notification
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error creating system notification: {str(e)}")
            return None
    
    @log_execution
    def get_agent_notifications(self, 
                               agent_id: int,
                               status: Optional[str] = None,
                               limit: int = 50) -> List[AgentNotification]:
        """
        Get notifications for an agent.
        
        Args:
            agent_id: ID of the agent
            status: Filter by status (unread, read, dismissed)
            limit: Maximum number of notifications to return
            
        Returns:
            List of AgentNotification objects
        """
        try:
            query = db.session.query(AgentNotification).filter_by(agent_id=agent_id)
            
            if status:
                query = query.filter_by(status=status)
            
            notifications = query.order_by(
                AgentNotification.created_at.desc()
            ).limit(limit).all()
            
            return notifications
            
        except Exception as e:
            self.logger.error(f"Error getting agent notifications: {str(e)}")
            return []
    
    @log_execution
    def mark_notification_as_read(self, notification_id: int, agent_id: int) -> bool:
        """
        Mark a notification as read.
        
        Args:
            notification_id: ID of the notification
            agent_id: ID of the agent (for authorization)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            notification = db.session.query(AgentNotification).filter_by(
                id=notification_id,
                agent_id=agent_id
            ).first()
            
            if not notification:
                self.logger.warning(f"Notification {notification_id} not found for agent {agent_id}")
                return False
            
            notification.mark_as_read()
            db.session.commit()
            
            self.logger.info(f"Marked notification {notification_id} as read")
            return True
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error marking notification as read: {str(e)}")
            return False
    
    @log_execution
    def dismiss_notification(self, notification_id: int, agent_id: int) -> bool:
        """
        Dismiss a notification.
        
        Args:
            notification_id: ID of the notification
            agent_id: ID of the agent (for authorization)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            notification = db.session.query(AgentNotification).filter_by(
                id=notification_id,
                agent_id=agent_id
            ).first()
            
            if not notification:
                self.logger.warning(f"Notification {notification_id} not found for agent {agent_id}")
                return False
            
            notification.dismiss()
            db.session.commit()
            
            self.logger.info(f"Dismissed notification {notification_id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error dismissing notification: {str(e)}")
            return False
    
    @log_execution
    def get_notification_summary(self, agent_id: int) -> Dict[str, Any]:
        """
        Get notification summary for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Dictionary with notification counts and recent activity
        """
        try:
            # Count notifications by status
            unread_count = db.session.query(AgentNotification).filter_by(
                agent_id=agent_id,
                status='unread'
            ).count()
            
            high_priority_count = db.session.query(AgentNotification).filter_by(
                agent_id=agent_id,
                status='unread',
                priority='high'
            ).count()
            
            # Recent notifications (last 24 hours)
            since = _utcnow_naive() - timedelta(hours=24)
            recent_count = db.session.query(AgentNotification).filter(
                AgentNotification.agent_id == agent_id,
                AgentNotification.created_at >= since
            ).count()
            
            return {
                'unread_count': unread_count,
                'high_priority_count': high_priority_count,
                'recent_count_24h': recent_count,
                'timestamp': _utcnow_naive().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting notification summary: {str(e)}")
            return {
                'unread_count': 0,
                'high_priority_count': 0,
                'recent_count_24h': 0,
                'error': str(e),
                'timestamp': _utcnow_naive().isoformat()
            }
    
    @log_execution
    def _send_high_priority_email(self, 
                                 agent: Agent, 
                                 notification: AgentNotification,
                                 property_match: PropertyMatch,
                                 property_obj: Property,
                                 customer: Customer):
        """Send email alert for high-priority property match."""
        try:
            if not agent.email:
                self.logger.warning(f"No email address for agent {agent.id}")
                return
            
            subject = f"🔥 High-Priority Property Match ({int(property_match.match_score * 100)}%)"
            
            # Create HTML email content
            html_content = f"""
            <html>
            <body>
                <h2>High-Priority Property Match Alert</h2>
                <p>Hi {agent.name},</p>
                <p>We found an excellent match for one of your properties!</p>
                
                <div style="background-color: #f0f8ff; padding: 15px; border-left: 4px solid #0066cc; margin: 15px 0;">
                    <h3>Match Details</h3>
                    <p><strong>Customer:</strong> {customer.name}</p>
                    <p><strong>Property:</strong> {property_obj.address}</p>
                    <p><strong>Match Score:</strong> {int(property_match.match_score * 100)}%</p>
                    <p><strong>Customer Budget:</strong> ${customer.budget_min:,.0f} - ${customer.budget_max:,.0f}</p>
                    <p><strong>Property Price:</strong> ${property_obj.price:,.0f}</p>
                </div>
                
                <div style="background-color: #f9f9f9; padding: 15px; margin: 15px 0;">
                    <h3>Why This is a Great Match</h3>
                    <p>{notification.message}</p>
                </div>
                
                <p>
                    <a href="#" style="background-color: #0066cc; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        View Full Details
                    </a>
                </p>
                
                <p>This high-priority match was generated by our AI-powered recommendation system.</p>
                <p>Best regards,<br>Real Estate CRM System</p>
            </body>
            </html>
            """
            
            success = self._send_email(agent.email, subject, html_content, is_html=True)
            
            if success:
                notification.email_sent = True
                notification.email_sent_at = _utcnow_naive()
                db.session.commit()
                self.logger.info(f"Sent high-priority email to {agent.email}")
            
        except Exception as e:
            self.logger.error(f"Error sending high-priority email: {str(e)}")
    
    @log_execution
    def _send_system_notification_email(self, agent: Agent, notification: AgentNotification):
        """Send email for system notification."""
        try:
            if not agent.email:
                return
            
            subject = f"System Notification: {notification.title}"
            content = f"""
            Hi {agent.name},
            
            {notification.message}
            
            This is an automated notification from the Real Estate CRM system.
            
            Best regards,
            Real Estate CRM System
            """
            
            success = self._send_email(agent.email, subject, content)
            
            if success:
                notification.email_sent = True
                notification.email_sent_at = _utcnow_naive()
                db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error sending system notification email: {str(e)}")
    
    @log_execution
    def _send_email(self, to_email: str, subject: str, content: str, is_html: bool = False) -> bool:
        """
        Send email using SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            content: Email content
            is_html: Whether content is HTML
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.email_enabled:
                self.logger.debug("Email notifications disabled")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative') if is_html else MIMEText(content)
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            if is_html:
                text_part = MIMEText(content.replace('<br>', '\n').replace('<p>', '').replace('</p>', '\n'), 'plain')
                html_part = MIMEText(content, 'html')
                msg.attach(text_part)
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False
    
    @log_execution
    def send_daily_digest(self, agent_id: int) -> bool:
        """
        Send daily notification digest to an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            True if successful, False otherwise
        """
        try:
            agent = db.session.get(Agent, agent_id)
            if not agent or not agent.email:
                return False
            
            # Get unread notifications from last 24 hours
            since = _utcnow_naive() - timedelta(hours=24)
            notifications = db.session.query(AgentNotification).filter(
                AgentNotification.agent_id == agent_id,
                AgentNotification.status == 'unread',
                AgentNotification.created_at >= since
            ).order_by(AgentNotification.priority.desc(), AgentNotification.created_at.desc()).all()
            
            if not notifications:
                return True  # No notifications to send
            
            # Create digest content
            subject = f"Daily Notification Digest - {len(notifications)} new notifications"
            
            high_priority = [n for n in notifications if n.priority == 'high']
            normal_priority = [n for n in notifications if n.priority == 'normal']
            
            content = f"""
            Hi {agent.name},
            
            You have {len(notifications)} new notifications:
            
            """
            
            if high_priority:
                content += f"🔥 HIGH PRIORITY ({len(high_priority)}):\n"
                for notif in high_priority[:5]:  # Limit to 5
                    content += f"  • {notif.title}\n"
                content += "\n"
            
            if normal_priority:
                content += f"📋 NORMAL PRIORITY ({len(normal_priority)}):\n"
                for notif in normal_priority[:10]:  # Limit to 10
                    content += f"  • {notif.title}\n"
                content += "\n"
            
            content += """
            Log in to your dashboard to view full details and take action.
            
            Best regards,
            Real Estate CRM System
            """
            
            return self._send_email(agent.email, subject, content)
            
        except Exception as e:
            self.logger.error(f"Error sending daily digest: {str(e)}")
            return False


# Global instance
notification_service = NotificationService()
