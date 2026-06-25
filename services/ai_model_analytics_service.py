import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
import json
import os

from services.llm.providers.base import LLMProvider
from utils.execution_tracer import log_execution

logger = logging.getLogger("services.analytics_service")


class AIModelAnalytics:
    """Tracks AI model performance, usage metrics, and A/B test results."""

    def __init__(self):
        self.logger = logger
        # In-memory storage for analytics (in production, this would use a database or Redis)
        self._performance_metrics = defaultdict(list)
        self._usage_stats = defaultdict(int)
        self._ab_test_results = defaultdict(list)
        self._drift_alerts = []

    @log_execution
    def record_model_performance(
        self,
        model_name: str,
        operation: str,
        latency_ms: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record performance metrics for an AI model operation."""
        try:
            metric = {
                "timestamp": datetime.utcnow().isoformat(),
                "model_name": model_name,
                "operation": operation,
                "latency_ms": latency_ms,
                "success": success,
                "metadata": metadata or {}
            }

            key = f"{model_name}:{operation}"
            self._performance_metrics[key].append(metric)

            # Keep only last 1000 entries per key to prevent memory growth
            if len(self._performance_metrics[key]) > 1000:
                self._performance_metrics[key] = self._performance_metrics[key][-1000:]

            # Update usage stats
            self._usage_stats[f"{model_name}:{operation}:calls"] += 1
            if success:
                self._usage_stats[f"{model_name}:{operation}:success"] += 1
            else:
                self._usage_stats[f"{model_name}:{operation}:failures"] += 1

            self.logger.debug(
                f"Recorded performance for {model_name}.{operation}: "
                f"{latency_ms}ms, success={success}"
            )

        except Exception as e:
            self.logger.error(f"Failed to record model performance: {e}")

    @log_execution
    def record_ab_test_result(
        self,
        test_name: str,
        variant: str,
        user_id: Optional[str],
        outcome: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> None:
        """Record an A/B test result."""
        try:
            result = {
                "timestamp": (timestamp or datetime.utcnow()).isoformat(),
                "test_name": test_name,
                "variant": variant,
                "user_id": user_id,
                "outcome": outcome
            }

            self._ab_test_results[test_name].append(result)

            # Keep only last 500 results per test
            if len(self._ab_test_results[test_name]) > 500:
                self._ab_test_results[test_name] = self._ab_test_results[test_name][-500:]

            self.logger.debug(
                f"Recorded A/B test result for {test_name}.{variant}: {outcome}"
            )

        except Exception as e:
            self.logger.error(f"Failed to record A/B test result: {e}")

    @log_execution
    def get_model_performance_stats(
        self,
        model_name: Optional[str] = None,
        operation: Optional[str] = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get performance statistics for models."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            stats = {}

            for key, metrics in self._performance_metrics.items():
                model, op = key.split(":", 1) if ":" in key else (key, "unknown")

                # Filter by model and operation if specified
                if model_name and model != model_name:
                    continue
                if operation and op != operation:
                    continue

                # Filter by time
                recent_metrics = [
                    m for m in metrics
                    if datetime.fromisoformat(m["timestamp"]) >= cutoff_time
                ]

                if not recent_metrics:
                    continue

                # Calculate statistics
                latencies = [m["latency_ms"] for m in recent_metrics]
                successes = [m["success"] for m in recent_metrics]

                stats[key] = {
                    "total_calls": len(recent_metrics),
                    "success_rate": sum(successes) / len(successes) if successes else 0,
                    "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
                    "min_latency_ms": min(latencies) if latencies else 0,
                    "max_latency_ms": max(latencies) if latencies else 0,
                    "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
                    "time_window_hours": hours
                }

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get model performance stats: {e}")
            return {}

    @log_execution
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get overall usage statistics."""
        try:
            return dict(self._usage_stats)
        except Exception as e:
            self.logger.error(f"Failed to get usage stats: {e}")
            return {}

    @log_execution
    def get_ab_test_results(
        self,
        test_name: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get A/B test results."""
        try:
            if test_name:
                results = self._ab_test_results.get(test_name, [])
                return {
                    test_name: results[-limit:] if results else []
                }
            else:
                # Return all tests with limited results
                return {
                    name: results[-limit:] if results else []
                    for name, results in self._ab_test_results.items()
                }
        except Exception as e:
            self.logger.error(f"Failed to get A/B test results: {e}")
            return {}

    @log_execution
    def detect_performance_drift(
        self,
        model_name: str,
        operation: str,
        baseline_hours: int = 168,  # 1 week
        comparison_hours: int = 24,  # Last 24 hours
        latency_threshold: float = 2.0,  # 2x baseline latency
        error_rate_threshold: float = 0.1  # 10% error rate increase
    ) -> List[Dict[str, Any]]:
        """Detect performance drift by comparing recent performance to baseline."""
        try:
            alerts = []
            key = f"{model_name}:{operation}"

            if key not in self._performance_metrics:
                return alerts

            metrics = self._performance_metrics[key]
            if not metrics:
                return alerts

            # Split into baseline and comparison periods
            now = datetime.utcnow()
            baseline_start = now - timedelta(hours=baseline_hours)
            comparison_start = now - timedelta(hours=comparison_hours)

            baseline_metrics = [
                m for m in metrics
                if baseline_start <= datetime.fromisoformat(m["timestamp"]) < comparison_start
            ]

            comparison_metrics = [
                m for m in metrics
                if datetime.fromisoformat(m["timestamp"]) >= comparison_start
            ]

            if not baseline_metrics or not comparison_metrics:
                return alerts  # Not enough data

            # Calculate baseline statistics
            baseline_latencies = [m["latency_ms"] for m in baseline_metrics]
            baseline_successes = [m["success"] for m in baseline_metrics]

            baseline_avg_latency = sum(baseline_latencies) / len(baseline_latencies)
            baseline_error_rate = 1 - (sum(baseline_successes) / len(baseline_successes))

            # Calculate comparison statistics
            comparison_latencies = [m["latency_ms"] for m in comparison_metrics]
            comparison_successes = [m["success"] for m in comparison_metrics]

            comparison_avg_latency = sum(comparison_latencies) / len(comparison_latencies)
            comparison_error_rate = 1 - (sum(comparison_successes) / len(comparison_successes))

            # Check for drift
            latency_ratio = comparison_avg_latency / baseline_avg_latency if baseline_avg_latency > 0 else 0
            error_rate_increase = comparison_error_rate - baseline_error_rate

            if latency_ratio > latency_threshold:
                alerts.append({
                    "type": "latency_drift",
                    "model_name": model_name,
                    "operation": operation,
                    "baseline_avg_latency_ms": baseline_avg_latency,
                    "comparison_avg_latency_ms": comparison_avg_latency,
                    "latency_ratio": latency_ratio,
                    "threshold": latency_threshold,
                    "detected_at": datetime.utcnow().isoformat()
                })

            if error_rate_increase > error_rate_threshold:
                alerts.append({
                    "type": "error_rate_drift",
                    "model_name": model_name,
                    "operation": operation,
                    "baseline_error_rate": baseline_error_rate,
                    "comparison_error_rate": comparison_error_rate,
                    "error_rate_increase": error_rate_increase,
                    "threshold": error_rate_threshold,
                    "detected_at": datetime.utcnow().isoformat()
                })

            # Store alerts
            self._drift_alerts.extend(alerts)
            # Keep only last 100 alerts
            if len(self._drift_alerts) > 100:
                self._drift_alerts = self._drift_alerts[-100:]

            return alerts

        except Exception as e:
            self.logger.error(f"Failed to detect performance drift: {e}")
            return []

    @log_execution
    def record_gemini_service_interaction(
        self,
        operation: str,
        latency_ms: float,
        success: bool,
        customer_id: Optional[int] = None,
        property_count: int = 0,
        conversation_length: int = 0
    ) -> None:
        """Record a Gemini service interaction specifically for tracking."""
        metadata = {
            "customer_id": customer_id,
            "property_count": property_count,
            "conversation_length": conversation_length
        }
        self.record_model_performance(
            model_name="gemini",
            operation=operation,
            latency_ms=latency_ms,
            success=success,
            metadata=metadata
        )

    @log_execution
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get a summary of all analytics data."""
        try:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "usage_stats": self.get_usage_stats(),
                "performance_stats": self.get_model_performance_stats(hours=24),
                "ab_test_counts": {
                    test_name: len(results)
                    for test_name, results in self._ab_test_results.items()
                },
                "recent_drift_alerts": self._drift_alerts[-10:] if self._drift_alerts else [],
                "total_tracked_operations": len(self._performance_metrics)
            }
        except Exception as e:
            self.logger.error(f"Failed to get analytics summary: {e}")
            return {"error": str(e)}


# Global service instance
ai_analytics = AIModelAnalytics()


@log_execution
def record_gemini_reasoning_operation(
    customer_id: Optional[int],
    property_id: Optional[int],
    latency_ms: float,
    success: bool,
    conversation_history_length: int = 0,
    reasoning_type: str = "standard"
) -> None:
    """Convenience function to record Gemini reasoning operations."""
    ai_analytics.record_gemini_service_interaction(
        operation=f"reasoning_{reasoning_type}",
        latency_ms=latency_ms,
        success=success,
        customer_id=customer_id,
        property_count=1 if property_id else 0,
        conversation_length=conversation_history_length
    )


@log_execution
def record_property_recommendation_operation(
    customer_id: Optional[int],
    properties_count: int,
    latency_ms: float,
    success: bool,
    has_conversation_history: bool = False
) -> None:
    """Convenience function to record property recommendation operations."""
    ai_analytics.record_gemini_service_interaction(
        operation="property_recommendations",
        latency_ms=latency_ms,
        success=success,
        customer_id=customer_id,
        property_count=properties_count,
        conversation_length=5 if has_conversation_history else 0  # Approximate
    )