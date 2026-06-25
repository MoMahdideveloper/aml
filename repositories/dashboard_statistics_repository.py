from typing import Dict, List, Optional, TypedDict
from datetime import datetime, timezone

from sqlalchemy import desc, func
from sqlalchemy.orm import joinedload

from database import db
from repositories.base_repository import BaseRepository
from sqlalchemy_models import Agent, Customer, Deal, Property, Task


class DashboardStatsDict(TypedDict):
    total_properties: int
    active_properties: int
    total_agents: int
    total_customers: int
    total_deals: int
    active_deals: int
    total_deal_value: float
    active_deal_value: float
    avg_property_price: float
    recent_properties: List[Property]
    recent_deals: List[Deal]
    median_price_trend: str
    avg_days_on_market_trend: str
    months_of_supply_trend: str
    price_per_sqft_trend: str


class RecentActivitiesDict(TypedDict):
    recent_properties: List[Property]
    recent_deals: List[Deal]
    recent_tasks: List[Task]


class PerformanceMetricsDict(TypedDict):
    win_rate: float
    loss_rate: float
    avg_deal_value: float
    avg_property_price: float
    total_deals: int
    won_deals: int
    lost_deals: int


class DashboardStatisticsRepository(BaseRepository):
    """Repository for dashboard statistics and aggregations"""

    def __init__(self):
        # This repository doesn't operate on a single model, so we don't call super().__init__()
        pass

    def get_dashboard_stats(self) -> DashboardStatsDict:
        """Get dashboard statistics"""
        total_properties = Property.query.filter(Property.is_deleted.is_(False)).count()
        active_properties = Property.query.filter(
            Property.status == "active",
            Property.is_deleted.is_(False),
        ).count()
        total_agents = Agent.query.filter(Agent.is_deleted.is_(False)).count()
        total_customers = Customer.query.filter(Customer.is_deleted.is_(False)).count()
        total_deals = Deal.query.filter(Deal.is_deleted.is_(False)).count()
        active_deals = Deal.query.filter(
            Deal.status.in_(["prospecting", "qualified", "proposal", "negotiation"]),
            Deal.is_deleted.is_(False),
        ).count()

        # Calculate deal values
        total_deal_value = (
            db.session.query(func.sum(Deal.offer_amount))
            .filter(Deal.is_deleted.is_(False))
            .scalar()
            or 0
        )
        active_deal_value = (
            db.session.query(func.sum(Deal.offer_amount))
            .filter(
                Deal.status.in_(["prospecting", "qualified", "proposal", "negotiation"]),
                Deal.is_deleted.is_(False),
            )
            .scalar()
            or 0
        )

        # Recent activities
        recent_properties = (
            Property.query.filter(Property.is_deleted.is_(False))
            .order_by(desc(Property.created_at))
            .limit(5)
            .all()
        )
        recent_deals = (
            Deal.query.filter(Deal.is_deleted.is_(False))
            .order_by(desc(Deal.created_at))
            .limit(5)
            .all()
        )

        # Calculate average property price
        avg_property_price = (
            db.session.query(func.avg(Property.price))
            .filter(Property.price > 0, Property.is_deleted.is_(False))
            .scalar()
            or 0
        )

        # Calculate trend metrics (placeholder values)
        median_price_trend = self._calculate_median_price_trend()
        avg_days_on_market_trend = self._calculate_avg_days_on_market_trend()
        months_of_supply_trend = self._calculate_months_of_supply_trend()
        price_per_sqft_trend = self._calculate_price_per_sqft_trend()

        return {
            "total_properties": total_properties,
            "active_properties": active_properties,
            "total_agents": total_agents,
            "total_customers": total_customers,
            "total_deals": total_deals,
            "active_deals": active_deals,
            "total_deal_value": total_deal_value,
            "active_deal_value": active_deal_value,
            "avg_property_price": avg_property_price,
            "recent_properties": recent_properties,
            "recent_deals": recent_deals,
            "median_price_trend": median_price_trend,
            "avg_days_on_market_trend": avg_days_on_market_trend,
            "months_of_supply_trend": months_of_supply_trend,
            "price_per_sqft_trend": price_per_sqft_trend,
        }

    def _calculate_median_price_trend(self) -> str:
        """Calculate YoY change in median property price"""
        # Placeholder logic - returns +5.2%
        return "+5.2%"

    def _calculate_avg_days_on_market_trend(self) -> str:
        """Calculate MoM change in average days on market"""
        # Placeholder logic - returns -2
        return "-2"

    def _calculate_months_of_supply_trend(self) -> str:
        """Calculate MoM change in months of supply"""
        # Placeholder logic - returns "Stable"
        return "Stable"

    def _calculate_price_per_sqft_trend(self) -> str:
        """Calculate YoY change in price per square foot"""
        # Placeholder logic - returns +3.8%
        return "+3.8%"

    def get_recent_activities(self, limit: int = 10) -> RecentActivitiesDict:
        """Get recent activities across entities"""
        recent_properties = (
            Property.query.filter(Property.is_deleted.is_(False))
            .order_by(desc(Property.created_at))
            .limit(limit)
            .all()
        )
        recent_deals = (
            Deal.query.filter(Deal.is_deleted.is_(False))
            .order_by(desc(Deal.created_at))
            .limit(limit)
            .all()
        )
        recent_tasks = (
            Task.query.filter(Task.is_deleted.is_(False))
            .order_by(desc(Task.created_at))
            .limit(limit)
            .all()
        )

        return {
            "recent_properties": recent_properties,
            "recent_deals": recent_deals,
            "recent_tasks": recent_tasks,
        }

    def get_performance_metrics(self) -> PerformanceMetricsDict:
        """Get performance metrics for the dashboard"""
        # Conversion rates
        total_deals = Deal.query.filter(Deal.is_deleted.is_(False)).count()
        won_deals = Deal.query.filter(
            Deal.status == "closed_won",
            Deal.is_deleted.is_(False),
        ).count()
        lost_deals = Deal.query.filter(
            Deal.status == "closed_lost",
            Deal.is_deleted.is_(False),
        ).count()

        win_rate = (won_deals / total_deals * 100) if total_deals > 0 else 0
        loss_rate = (lost_deals / total_deals * 100) if total_deals > 0 else 0

        # Average deal value
        avg_deal_value = (
            db.session.query(func.avg(Deal.offer_amount))
            .filter(Deal.is_deleted.is_(False))
            .scalar()
            or 0
        )

        # Average property price
        avg_property_price = (
            db.session.query(func.avg(Property.price))
            .filter(Property.price > 0, Property.is_deleted.is_(False))
            .scalar()
            or 0
        )

        return {
            "win_rate": win_rate,
            "loss_rate": loss_rate,
            "avg_deal_value": avg_deal_value,
            "avg_property_price": avg_property_price,
            "total_deals": total_deals,
            "won_deals": won_deals,
            "lost_deals": lost_deals,
        }