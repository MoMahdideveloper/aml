"""
Workflow service for smart task prioritization and document processing.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from sqlalchemy_models import Task, Deal, Customer, Property, Agent
from database import db
from services.gemini_service import gemini_service
from utils.execution_tracer import log_execution

logger = logging.getLogger("services.workflow_service")


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    """Task statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class WorkflowService:
    """Service for workflow automation, task prioritization, and document processing."""

    def __init__(self):
        self.logger = logging.getLogger("services.workflow_service")

    @log_execution
    def prioritize_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        Prioritize tasks based on multiple factors:
        - Due date (sooner = higher priority)
        - Explicit priority field
        - Blocking relationships (tasks blocking others get higher priority)
        - Age (older tasks may get higher priority)
        - Associated deal/customer value

        Args:
            tasks: List of Task objects to prioritize

        Returns:
            List of tasks sorted by priority (highest first)
        """
        if not tasks:
            return []

        scored_tasks = []
        now = datetime.utcnow()

        for task in tasks:
            score = self._calculate_task_priority_score(task, now)
            scored_tasks.append((score, task))

        # Sort by score descending (higher score = higher priority)
        sorted_tasks = [task for score, task in sorted(scored_tasks, key=lambda x: x[0], reverse=True)]
        return sorted_tasks

    @log_execution
    def _calculate_task_priority_score(self, task: Task, now: datetime) -> float:
        """Calculate a priority score for a task."""
        score = 0.0

        # 1. Due date factor (sooner = 0-40 points)
        if task.due_date:
            days_until_due = (task.due_date - now).days
            if days_until_due < 0:
                # Overdue: maximum urgency
                due_score = 40
            elif days_until_due == 0:
                # Due today
                due_score = 35
            elif days_until_due <= 1:
                # Due tomorrow
                due_score = 30
            elif days_until_due <= 3:
                # Due in next few days
                due_score = 25
            elif days_until_due <= 7:
                # Due next week
                due_score = 20
            else:
                # Due later: decreasing points
                due_score = max(0, 20 - (days_until_due // 7))
        else:
            # No due date: lower priority
            due_score = 10
        score += due_score

        # 2. Explicit priority field = 0-30 points
        priority_scores = {
            TaskPriority.LOW.value: 5,
            TaskPriority.MEDIUM.value: 15,
            TaskPriority.HIGH.value: 25,
            TaskPriority.URGENT.value: 30
        }
        priority_score = priority_scores.get(task.priority, 15)  # Default to medium
        score += priority_score

        # 3. Blocking factor = 0-20 points
        # Count how many tasks this one blocks (more blockers = higher priority)
        blocking_count = self._count_blocked_tasks(task.id)
        blocking_score = min(20, blocking_count * 5)  # 5 points per blocked task, max 20
        score += blocking_score

        # 4. Age factor = 0-10 points (older tasks get slightly higher priority)
        if task.created_at:
            age_days = (now - task.created_at).days
            age_score = min(10, age_days // 10)  # 1 point per 10 days, max 10
            score += age_score

        # 5. Associated entity value = 0-10 points
        value_score = self._get_associated_entity_value(task)
        score += value_score

        return score

    @log_execution
    def _count_blocked_tasks(self, task_id: int) -> int:
        """Count how many tasks are blocked by the given task."""
        # This assumes we have a way to track task dependencies.
        # For simplicity, we'll return 0 if we don't have dependency tracking.
        # In a real system, you'd have a task_dependencies table.
        try:
            # Example: if we have a table TaskDependency with blocker_id and blocked_id
            # For now, we'll return 0 as placeholder
            return 0
        except Exception:
            return 0

    @log_execution
    def _get_associated_entity_value(self, task: Task) -> float:
        """Get value score based on associated deal/customer/property."""
        score = 0.0

        # Check associated deal
        if task.deal_id:
            deal = db.session.get(Deal, task.deal_id)
            if deal and deal.offer_amount:
                # Higher value deals get higher scores
                amount = float(deal.offer_amount)
                if amount >= 1000000:  # 1M+
                    score = 10
                elif amount >= 500000:  # 500K+
                    score = 8
                elif amount >= 100000:  # 100K+
                    score = 5
                else:
                    score = 2

        # Check associated customer (if no deal)
        elif task.customer_id:
            customer = db.session.get(Customer, task.customer_id)
            if customer:
                # Could look at customer's total deal value or potential
                # For now, give a small boost
                score = 3

        # Check associated property
        elif task.property_id:
            property_obj = db.session.get(Property, task.property_id)
            if property_obj and property_obj.price:
                price = float(property_obj.price)
                if price >= 500000:
                    score = 5
                elif price >= 200000:
                    score = 3
                else:
                    score = 1

        return score

    @log_execution
    def process_document(self, file_data: bytes, filename: str, mime_type: str) -> Dict[str, Any]:
        """
        Process a document (image or PDF) to extract relevant information for the CRM.
        This could include:
        - Property details from property listings/flyers
        - Customer information from IDs or forms
        - Deal terms from contracts
        - etc.

        Args:
            file_data: Raw file bytes
            filename: Original filename
            mime_type: MIME type of the file

        Returns:
            Dictionary containing extracted information and metadata
        """
        try:
            self.logger.info(f"Processing document: {filename} ({mime_type})")

            # Route to appropriate processor based on mime type
            if mime_type.startswith("image/"):
                return self._process_image(file_data, filename)
            elif mime_type == "application/pdf":
                return self._process_pdf(file_data, filename)
            elif mime_type.startswith("text/"):
                return self._process_text(file_data, filename)
            else:
                # Unsupported type
                return {
                    "success": False,
                    "error": f"Unsupported file type: {mime_type}",
                    "extracted_data": {}
                }

        except Exception as e:
            self.logger.error(f"Error processing document {filename}: {e}")
            return {
                "success": False,
                "error": str(e),
                "extracted_data": {}
            }

    @log_execution
    def _process_image(self, image_data: bytes, filename: str) -> Dict[str, Any]:
        """Process an image file to extract information."""
        try:
            # Use Gemini service to extract property or customer info from image
            # First, try to extract as property
            property_data = gemini_service.extract_property_from_image(image_data, "image/jpeg")  # Assume JPEG for now

            # If we got reasonable property data, return it
            if property_data and property_data.get("data"):
                return {
                    "success": True,
                    "document_type": "property_document",
                    "extracted_data": property_data["data"],
                    "confidence": property_data.get("confidence", 0.5),
                    "suggested_action": "property_extraction"
                }
            else:
                # Try to extract as customer
                # For images, we would need OCR first to get text; for now we'll note limitation
                return {
                    "success": True,
                    "document_type": "image",
                    "extracted_data": {"filename": filename, "type": "image"},
                    "confidence": 0.3,
                    "message": "Image processed but no specific entity extracted. Consider using OCR first."
                }

        except Exception as e:
            self.logger.error(f"Error processing image {filename}: {e}")
            return {
                "success": False,
                "error": str(e),
                "extracted_data": {}
            }

    @log_execution
    def _process_pdf(self, pdf_data: bytes, filename: str) -> Dict[str, Any]:
        """Process a PDF file to extract information."""
        # Placeholder implementation
        # In a real system, we'd use a PDF parsing library (like PyPDF2, pdfplumber) or OCR for scanned PDFs
        self.logger.info(f"PDF processing not fully implemented for {filename}")
        return {
            "success": True,
            "document_type": "pdf",
            "extracted_data": {"filename": filename, "type": "pdf", "size_bytes": len(pdf_data)},
            "confidence": 0.4,
            "message": "PDF processing placeholder - text extraction not implemented"
        }

    @log_execution
    def _process_text(self, text_data: bytes, filename: str) -> Dict[str, Any]:
        """Process a text file to extract information."""
        try:
            text = text_data.decode('utf-8')

            # Try to extract customer information first
            customer_data = gemini_service.extract_customer_from_text(text)
            if customer_data.get("data") and any(customer_data["data"].values()):
                return {
                    "success": True,
                    "document_type": "customer_document",
                    "extracted_data": customer_data["data"],
                    "confidence": customer_data.get("confidence", 0.5),
                    "missing_fields": customer_data.get("missing", [])
                }

            # Try to extract property information
            property_data = gemini_service.extract_property_from_text(text)
            if property_data.get("data") and any(property_data["data"].values()):
                return {
                    "success": True,
                    "document_type": "property_document",
                    "extracted_data": property_data["data"],
                    "confidence": property_data.get("confidence", 0.5),
                    "missing_fields": property_data.get("missing", [])
                }

            # If neither, return generic text info
            return {
                "success": True,
                "document_type": "text",
                "extracted_data": {
                    "filename": filename,
                    "text_preview": text[:500] + "..." if len(text) > 500 else text,
                    "length": len(text)
                },
                "confidence": 0.3
            }

        except UnicodeDecodeError:
            return {
                "success": False,
                "error": "Unable to decode text file as UTF-8",
                "extracted_data": {}
            }
        except Exception as e:
            self.logger.error(f"Error processing text file {filename}: {e}")
            return {
                "success": False,
                "error": str(e),
                "extracted_data": {}
            }

    @log_execution
    def get_workflow_suggestions(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Generate workflow suggestions for a user based on their current tasks,
        deals, and calendar.

        Args:
            user_id: ID of the user/agent

        Returns:
            List of suggested actions
        """
        suggestions = []

        try:
            # Get user's assigned tasks
            agent = db.session.get(Agent, user_id)
            if not agent:
                return [{"type": "error", "message": "Agent not found"}]

            tasks = db.session.query(Task).filter(
                Task.agent_id == user_id,
                Task.status.in_([TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value])
            ).all()

            # Prioritize the tasks
            prioritized_tasks = self.prioritize_tasks(tasks)

            # Suggest top 3 priority tasks
            for i, task in enumerate(prioritized_tasks[:3]):
                suggestions.append({
                    "type": "task_priority",
                    "priority": i + 1,
                    "task_id": task.id,
                    "title": task.title,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                    "message": f"Focus on '{task.title}' (priority {i+1})"
                })

            # Check for overdue tasks
            overdue_tasks = [t for t in tasks if t.due_date and t.due_date < datetime.utcnow() and t.status != TaskStatus.COMPLETED.value]
            if overdue_tasks:
                suggestions.append({
                    "type": "overdue_alert",
                    "count": len(overdue_tasks),
                    "message": f"You have {len(overdue_tasks)} overdue task(s). Consider addressing them first."
                })

        except Exception as e:
            self.logger.error(f"Error generating workflow suggestions for user {user_id}: {e}")
            suggestions.append({
                "type": "error",
                "message": "Failed to generate workflow suggestions"
            })

        return suggestions

# Create singleton instance
workflow_service = WorkflowService()