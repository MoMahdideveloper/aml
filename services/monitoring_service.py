import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque

from database import db
from sqlalchemy import text
from sqlalchemy_models import PropertyMatch, AgentNotification, Property, Customer
from utils.execution_tracer import log_execution


class MonitoringService:
    """
    Monitoring and logging service for background matching processes.
    
    Handles:
    - Performance monitoring and metrics collection
    - Error tracking and logging
    - System health checks
    - Background process statistics
    - Alert generation for system issues
    """
    
    def __init__(self):
        self.logger = logging.getLogger("services.monitoring_service")
        
        # In-memory metrics storage (limited size)
        self.metrics_buffer = deque(maxlen=1000)
        self.error_buffer = deque(maxlen=100)
        self.performance_buffer = deque(maxlen=500)
        
        # Performance thresholds
        self.slow_job_threshold = 60.0  # seconds
        self.high_error_rate_threshold = 0.1  # 10% error rate
        self.memory_usage_threshold = 0.8  # 80% memory usage
        
        # Monitoring intervals
        self.health_check_interval = 300  # 5 minutes
        self.last_health_check = datetime.utcnow()
    
    @log_execution
    def log_matching_job_start(self, job_id: str, job_type: str = 'scheduled') -> str:
        """
        Log the start of a matching job.
        
        Args:
            job_id: Unique identifier for the job
            job_type: Type of job (scheduled, immediate, manual)
            
        Returns:
            Session ID for tracking this job execution
        """
        session_id = f"{job_id}_{int(time.time() * 1000)}"
        
        metric = {
            'type': 'job_start',
            'session_id': session_id,
            'job_id': job_id,
            'job_type': job_type,
            'timestamp': datetime.utcnow().isoformat(),
            'start_time': time.time()
        }
        
        self.metrics_buffer.append(metric)
        self.logger.info(f"Matching job started: {job_id} (session: {session_id})")
        
        return session_id
    
    @log_execution
    def log_matching_job_completion(self, 
                                   session_id: str,
                                   result: Dict[str, Any],
                                   duration: float = None):
        """
        Log the completion of a matching job.
        
        Args:
            session_id: Session ID from job start
            result: Result dictionary from the matching process
            duration: Job duration in seconds (optional, will be calculated if not provided)
        """
        try:
            # Find the corresponding start event
            start_event = None
            for metric in reversed(self.metrics_buffer):
                if metric.get('session_id') == session_id and metric.get('type') == 'job_start':
                    start_event = metric
                    break
            
            if not start_event:
                self.logger.warning(f"No start event found for session {session_id}")
                return
            
            # Calculate duration if not provided
            if duration is None:
                duration = time.time() - start_event.get('start_time', time.time())
            
            # Create completion metric
            metric = {
                'type': 'job_completion',
                'session_id': session_id,
                'job_id': start_event.get('job_id'),
                'job_type': start_event.get('job_type'),
                'timestamp': datetime.utcnow().isoformat(),
                'duration_seconds': duration,
                'result': result,
                'status': result.get('status', 'unknown')
            }
            
            self.metrics_buffer.append(metric)
            self.performance_buffer.append({
                'duration': duration,
                'matches_found': result.get('matches_found', 0),
                'matches_saved': result.get('matches_saved', 0),
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Check for performance issues
            if duration > self.slow_job_threshold:
                self.logger.warning(f"Slow matching job detected: {duration:.2f}s (session: {session_id})")
                self._alert_slow_job(session_id, duration, result)
            
            self.logger.info(f"Matching job completed: {session_id} in {duration:.2f}s - {result}")
            
        except Exception as e:
            self.logger.error(f"Error logging job completion: {str(e)}")
    
    @log_execution
    def log_matching_error(self, 
                          session_id: str,
                          error: Exception,
                          context: Dict[str, Any] = None):
        """
        Log an error during matching process.
        
        Args:
            session_id: Session ID for the job
            error: Exception that occurred
            context: Additional context about the error
        """
        try:
            error_record = {
                'type': 'matching_error',
                'session_id': session_id,
                'timestamp': datetime.utcnow().isoformat(),
                'error_type': type(error).__name__,
                'error_message': str(error),
                'context': context or {}
            }
            
            self.error_buffer.append(error_record)
            self.logger.error(f"Matching error in session {session_id}: {error}", exc_info=True)
            
            # Check error rate
            self._check_error_rate()
            
        except Exception as e:
            self.logger.error(f"Error logging matching error: {str(e)}")
    
    @log_execution
    def log_notification_activity(self, 
                                 activity_type: str,
                                 agent_id: int,
                                 notification_id: int = None,
                                 details: Dict[str, Any] = None):
        """
        Log notification-related activity.
        
        Args:
            activity_type: Type of activity (created, sent, read, dismissed)
            agent_id: ID of the agent
            notification_id: ID of the notification (optional)
            details: Additional details about the activity
        """
        try:
            metric = {
                'type': 'notification_activity',
                'activity_type': activity_type,
                'agent_id': agent_id,
                'notification_id': notification_id,
                'timestamp': datetime.utcnow().isoformat(),
                'details': details or {}
            }
            
            self.metrics_buffer.append(metric)
            self.logger.debug(f"Notification activity: {activity_type} for agent {agent_id}")
            
        except Exception as e:
            self.logger.error(f"Error logging notification activity: {str(e)}")
    
    @log_execution
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status.
        
        Returns:
            Dictionary with system health metrics
        """
        try:
            now = datetime.utcnow()
            
            # Basic database health
            db_health = self._check_database_health()
            
            # Recent job performance
            job_performance = self._get_job_performance_metrics()
            
            # Error rates
            error_metrics = self._get_error_metrics()
            
            # Notification statistics
            notification_stats = self._get_notification_statistics()
            
            # System resource usage (basic)
            resource_usage = self._get_resource_usage()
            
            health_status = {
                'timestamp': now.isoformat(),
                'overall_status': 'healthy',  # Will be updated based on checks
                'database': db_health,
                'job_performance': job_performance,
                'errors': error_metrics,
                'notifications': notification_stats,
                'resources': resource_usage,
                'last_health_check': self.last_health_check.isoformat()
            }
            
            # Determine overall status
            health_status['overall_status'] = self._determine_overall_health(health_status)
            
            self.last_health_check = now
            return health_status
            
        except Exception as e:
            self.logger.error(f"Error getting system health: {str(e)}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'overall_status': 'error',
                'error': str(e)
            }
    
    @log_execution
    def get_performance_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get performance metrics for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Filter recent performance data
            recent_performance = [
                p for p in self.performance_buffer 
                if datetime.fromisoformat(p['timestamp']) >= cutoff_time
            ]
            
            if not recent_performance:
                return {
                    'period_hours': hours,
                    'job_count': 0,
                    'avg_duration': 0,
                    'total_matches': 0,
                    'avg_matches_per_job': 0,
                    'success_count': 0,
                    'failure_count': 0,
                    'p50_duration': 0,
                    'p95_duration': 0,
                }
            
            # Calculate metrics
            durations = [p['duration'] for p in recent_performance]
            matches_found = [p['matches_found'] for p in recent_performance]
            matches_saved = [p['matches_saved'] for p in recent_performance]
            completion_events = [
                m for m in self.metrics_buffer
                if m.get('type') == 'job_completion'
                and datetime.fromisoformat(m['timestamp']) >= cutoff_time
            ]
            success_count = len([m for m in completion_events if m.get('status') == 'completed'])
            failure_count = len([m for m in completion_events if m.get('status') in ('error', 'failed')])
            
            return {
                'period_hours': hours,
                'job_count': len(recent_performance),
                'avg_duration': sum(durations) / len(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'p50_duration': self._percentile(durations, 50),
                'p95_duration': self._percentile(durations, 95),
                'total_matches_found': sum(matches_found),
                'total_matches_saved': sum(matches_saved),
                'avg_matches_per_job': sum(matches_found) / len(matches_found) if matches_found else 0,
                'slow_jobs_count': len([d for d in durations if d > self.slow_job_threshold]),
                'success_count': success_count,
                'failure_count': failure_count,
            }
            
        except Exception as e:
            self.logger.error(f"Error getting performance metrics: {str(e)}")
            return {'error': str(e)}
    
    @log_execution
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get error summary for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with error summary
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Filter recent errors
            recent_errors = [
                e for e in self.error_buffer 
                if datetime.fromisoformat(e['timestamp']) >= cutoff_time
            ]
            
            # Group errors by type
            error_types = defaultdict(int)
            for error in recent_errors:
                error_types[error['error_type']] += 1
            
            return {
                'period_hours': hours,
                'total_errors': len(recent_errors),
                'error_types': dict(error_types),
                'recent_errors': recent_errors[-10:],  # Last 10 errors
                'error_rate': len(recent_errors) / max(1, len(self.performance_buffer))
            }
            
        except Exception as e:
            self.logger.error(f"Error getting error summary: {str(e)}")
            return {'error': str(e)}

    @log_execution
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Return percentile value using nearest-rank on sorted values."""
        if not values:
            return 0
        ordered = sorted(values)
        idx = max(0, min(len(ordered) - 1, int(round((percentile / 100) * (len(ordered) - 1)))))
        return ordered[idx]
    
    @log_execution
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and basic statistics."""
        try:
            # Test database connection
            db.session.execute(text("SELECT 1"))
            
            # Get basic counts
            property_count = db.session.query(Property).count()
            customer_count = db.session.query(Customer).count()
            match_count = db.session.query(PropertyMatch).count()
            notification_count = db.session.query(AgentNotification).count()
            
            return {
                'status': 'healthy',
                'properties': property_count,
                'customers': customer_count,
                'matches': match_count,
                'notifications': notification_count
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    @log_execution
    def _get_job_performance_metrics(self) -> Dict[str, Any]:
        """Get recent job performance metrics."""
        try:
            recent_completions = [
                m for m in self.metrics_buffer 
                if m.get('type') == 'job_completion'
                and datetime.fromisoformat(m['timestamp']) >= datetime.utcnow() - timedelta(hours=24)
            ]
            
            if not recent_completions:
                return {'jobs_24h': 0, 'avg_duration': 0}
            
            durations = [m.get('duration_seconds', 0) for m in recent_completions]
            successful_jobs = [m for m in recent_completions if m.get('status') == 'completed']
            
            return {
                'jobs_24h': len(recent_completions),
                'successful_jobs': len(successful_jobs),
                'avg_duration': sum(durations) / len(durations) if durations else 0,
                'slow_jobs': len([d for d in durations if d > self.slow_job_threshold])
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    @log_execution
    def _get_error_metrics(self) -> Dict[str, Any]:
        """Get recent error metrics."""
        try:
            recent_errors = [
                e for e in self.error_buffer 
                if datetime.fromisoformat(e['timestamp']) >= datetime.utcnow() - timedelta(hours=24)
            ]
            
            error_rate = len(recent_errors) / max(1, len([
                m for m in self.metrics_buffer 
                if m.get('type') == 'job_completion'
                and datetime.fromisoformat(m['timestamp']) >= datetime.utcnow() - timedelta(hours=24)
            ]))
            
            return {
                'errors_24h': len(recent_errors),
                'error_rate': error_rate,
                'high_error_rate': error_rate > self.high_error_rate_threshold
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    @log_execution
    def _get_notification_statistics(self) -> Dict[str, Any]:
        """Get notification system statistics."""
        try:
            # Recent notification activity
            recent_notifications = [
                m for m in self.metrics_buffer 
                if m.get('type') == 'notification_activity'
                and datetime.fromisoformat(m['timestamp']) >= datetime.utcnow() - timedelta(hours=24)
            ]
            
            # Count by activity type
            activity_counts = defaultdict(int)
            for notif in recent_notifications:
                activity_counts[notif.get('activity_type')] += 1
            
            return {
                'notifications_24h': len(recent_notifications),
                'activity_breakdown': dict(activity_counts),
                'unread_count': db.session.query(AgentNotification).filter_by(status='unread').count()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    @log_execution
    def _get_resource_usage(self) -> Dict[str, Any]:
        """Get basic resource usage metrics."""
        try:
            import psutil
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                'memory_percent': memory.percent / 100.0,
                'memory_available_gb': memory.available / (1024**3),
                'cpu_percent': cpu_percent / 100.0,
                'high_memory_usage': memory.percent > (self.memory_usage_threshold * 100)
            }
            
        except ImportError:
            return {'error': 'psutil not available'}
        except Exception as e:
            return {'error': str(e)}
    
    @log_execution
    def _determine_overall_health(self, health_data: Dict[str, Any]) -> str:
        """Determine overall system health status."""
        try:
            # Check for critical issues
            if health_data['database'].get('status') != 'healthy':
                return 'critical'
            
            # Check error rate
            if health_data['errors'].get('high_error_rate', False):
                return 'warning'
            
            # Check resource usage
            if health_data['resources'].get('high_memory_usage', False):
                return 'warning'
            
            # Check job performance
            if health_data['job_performance'].get('slow_jobs', 0) > 2:
                return 'warning'
            
            return 'healthy'
            
        except Exception as e:
            self.logger.error(f"Error determining overall health: {str(e)}")
            return 'unknown'
    
    @log_execution
    def _check_error_rate(self):
        """Check if error rate is too high and alert if needed."""
        try:
            recent_errors = len([
                e for e in self.error_buffer 
                if datetime.fromisoformat(e['timestamp']) >= datetime.utcnow() - timedelta(minutes=30)
            ])
            
            recent_jobs = len([
                m for m in self.metrics_buffer 
                if m.get('type') == 'job_completion'
                and datetime.fromisoformat(m['timestamp']) >= datetime.utcnow() - timedelta(minutes=30)
            ])
            
            if recent_jobs > 0:
                error_rate = recent_errors / recent_jobs
                if error_rate > self.high_error_rate_threshold:
                    self.logger.warning(f"High error rate detected: {error_rate:.2%} ({recent_errors}/{recent_jobs})")
            
        except Exception as e:
            self.logger.error(f"Error checking error rate: {str(e)}")
    
    @log_execution
    def _alert_slow_job(self, session_id: str, duration: float, result: Dict[str, Any]):
        """Generate alert for slow job execution."""
        try:
            self.logger.warning(
                f"PERFORMANCE ALERT: Slow matching job detected\n"
                f"Session ID: {session_id}\n"
                f"Duration: {duration:.2f}s (threshold: {self.slow_job_threshold}s)\n"
                f"Matches found: {result.get('matches_found', 0)}\n"
                f"Result: {result}"
            )
            
        except Exception as e:
            self.logger.error(f"Error generating slow job alert: {str(e)}")
    
    @log_execution
    def export_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Export all metrics for the specified time period.
        
        Args:
            hours: Number of hours to export
            
        Returns:
            Dictionary with all metrics data
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Filter all data by time period
            recent_metrics = [
                m for m in self.metrics_buffer 
                if datetime.fromisoformat(m['timestamp']) >= cutoff_time
            ]
            
            recent_errors = [
                e for e in self.error_buffer 
                if datetime.fromisoformat(e['timestamp']) >= cutoff_time
            ]
            
            recent_performance = [
                p for p in self.performance_buffer 
                if datetime.fromisoformat(p['timestamp']) >= cutoff_time
            ]
            
            return {
                'export_timestamp': datetime.utcnow().isoformat(),
                'period_hours': hours,
                'metrics': recent_metrics,
                'errors': recent_errors,
                'performance': recent_performance,
                'summary': {
                    'total_metrics': len(recent_metrics),
                    'total_errors': len(recent_errors),
                    'total_performance_records': len(recent_performance)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error exporting metrics: {str(e)}")
            return {'error': str(e)}


# Global instance
monitoring_service = MonitoringService()
