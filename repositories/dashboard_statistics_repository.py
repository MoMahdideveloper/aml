from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, TypedDict, Union

from sqlalchemy import desc, func

from database import db
from repositories.base_repository import BaseRepository
from sqlalchemy_models import (
    Agent,
    Customer,
    DashboardStatSnapshot,
    Deal,
    Property,
    Task,
)
from utils.time_utc import utc_now_naive

# Bento-card metrics that receive nested {value, trend} on the dashboard.
TREND_METRIC_KEYS = (
    "total_properties",
    "active_deals",
    "total_deal_value",
    "total_customers",
)

ACTIVE_DEAL_STATUSES = ("prospecting", "qualified", "proposal", "negotiation")


class TrendDict(TypedDict):
    direction: str
    icon: str
    sign: str
    percent: str


class MetricWithTrend(TypedDict):
    value: Union[int, float]
    trend: TrendDict


class DashboardStatsDict(TypedDict, total=False):
    total_properties: Union[int, MetricWithTrend]
    active_properties: int
    total_agents: int
    total_customers: Union[int, MetricWithTrend]
    total_deals: int
    active_deals: Union[int, MetricWithTrend]
    total_deal_value: Union[float, MetricWithTrend]
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


def calculate_trend_change(
    current: Optional[Union[int, float]],
    previous: Optional[Union[int, float]],
) -> Optional[float]:
    """Return percent change, or None when history is missing.

    Zero previous with non-zero current yields 0.0 (neutral) per product decision.
    """
    if previous is None or current is None:
        return None
    try:
        cur = float(current)
        prev = float(previous)
    except (TypeError, ValueError):
        return None
    if prev == 0:
        return 0.0
    return ((cur - prev) / prev) * 100.0


def format_trend(change: Optional[float]) -> TrendDict:
    """Convert a percent change into dashboard trend display fields."""
    if change is None:
        return {
            "direction": "neutral",
            "icon": "trending_flat",
            "sign": "",
            "percent": "0.0",
        }
    try:
        value = float(change)
    except (TypeError, ValueError):
        return {
            "direction": "neutral",
            "icon": "trending_flat",
            "sign": "",
            "percent": "0.0",
        }
    if abs(value) < 0.05:
        return {
            "direction": "neutral",
            "icon": "trending_flat",
            "sign": "",
            "percent": "0.0",
        }
    if value > 0:
        return {
            "direction": "up",
            "icon": "trending_up",
            "sign": "+",
            "percent": f"{abs(value):.1f}",
        }
    return {
        "direction": "down",
        "icon": "trending_down",
        "sign": "-",
        "percent": f"{abs(value):.1f}",
    }


class DashboardStatisticsRepository(BaseRepository):
    """Repository for dashboard statistics and aggregations"""

    def __init__(self):
        # This repository doesn't operate on a single model, so we don't call super().__init__()
        pass

    def collect_current_metrics(self) -> Dict[str, Union[int, float]]:
        """Collect live scalar metrics used for dashboard cards and snapshots."""
        total_properties = Property.query.filter(Property.is_deleted.is_(False)).count()
        active_properties = Property.query.filter(
            Property.status == "active",
            Property.is_deleted.is_(False),
        ).count()
        total_agents = Agent.query.filter(Agent.is_deleted.is_(False)).count()
        total_customers = Customer.query.filter(Customer.is_deleted.is_(False)).count()
        total_deals = Deal.query.filter(Deal.is_deleted.is_(False)).count()
        active_deals = Deal.query.filter(
            Deal.status.in_(list(ACTIVE_DEAL_STATUSES)),
            Deal.is_deleted.is_(False),
        ).count()

        total_deal_value = (
            db.session.query(func.sum(Deal.offer_amount))
            .filter(Deal.is_deleted.is_(False))
            .scalar()
            or 0
        )
        active_deal_value = (
            db.session.query(func.sum(Deal.offer_amount))
            .filter(
                Deal.status.in_(list(ACTIVE_DEAL_STATUSES)),
                Deal.is_deleted.is_(False),
            )
            .scalar()
            or 0
        )
        avg_property_price = (
            db.session.query(func.avg(Property.price))
            .filter(Property.price > 0, Property.is_deleted.is_(False))
            .scalar()
            or 0
        )

        return {
            "total_properties": int(total_properties),
            "active_properties": int(active_properties),
            "total_agents": int(total_agents),
            "total_customers": int(total_customers),
            "total_deals": int(total_deals),
            "active_deals": int(active_deals),
            "total_deal_value": float(total_deal_value or 0),
            "active_deal_value": float(active_deal_value or 0),
            "avg_property_price": float(avg_property_price or 0),
            "recent_properties_count": min(5, int(total_properties)),
            "recent_deals_count": min(5, int(total_deals)),
        }

    def create_daily_snapshot(
        self,
        metrics: Optional[Dict[str, Union[int, float]]] = None,
        now: Optional[datetime] = None,
    ) -> DashboardStatSnapshot:
        """Create today's snapshot once; return existing row if already present."""
        now = now or utc_now_naive()
        day = now.date() if isinstance(now, datetime) else date.today()
        day_start = datetime.combine(day, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        existing = (
            DashboardStatSnapshot.query.filter(
                DashboardStatSnapshot.timestamp >= day_start,
                DashboardStatSnapshot.timestamp < day_end,
            )
            .order_by(DashboardStatSnapshot.timestamp.desc())
            .first()
        )
        if existing is not None:
            return existing

        metrics = metrics or self.collect_current_metrics()
        snapshot = DashboardStatSnapshot(
            timestamp=now,
            total_properties=int(metrics.get("total_properties") or 0),
            active_properties=int(metrics.get("active_properties") or 0),
            total_agents=int(metrics.get("total_agents") or 0),
            total_customers=int(metrics.get("total_customers") or 0),
            total_deals=int(metrics.get("total_deals") or 0),
            active_deals=int(metrics.get("active_deals") or 0),
            total_deal_value=int(float(metrics.get("total_deal_value") or 0)),
            active_deal_value=int(float(metrics.get("active_deal_value") or 0)),
            avg_property_price=int(float(metrics.get("avg_property_price") or 0)),
            recent_properties_count=int(metrics.get("recent_properties_count") or 0),
            recent_deals_count=int(metrics.get("recent_deals_count") or 0),
        )
        db.session.add(snapshot)
        db.session.commit()
        return snapshot

    def get_historical_snapshot(
        self,
        days_ago: int = 30,
        window_days: int = 3,
        reference_date: Optional[date] = None,
    ) -> Optional[DashboardStatSnapshot]:
        """Find snapshot from ``days_ago``, or closest within ±``window_days``."""
        ref = reference_date or date.today()
        target = ref - timedelta(days=days_ago)
        window_start = datetime.combine(target - timedelta(days=window_days), datetime.min.time())
        window_end = datetime.combine(
            target + timedelta(days=window_days + 1), datetime.min.time()
        )

        candidates = (
            DashboardStatSnapshot.query.filter(
                DashboardStatSnapshot.timestamp >= window_start,
                DashboardStatSnapshot.timestamp < window_end,
            )
            .order_by(DashboardStatSnapshot.timestamp.asc())
            .all()
        )
        if not candidates:
            return None

        exact = [s for s in candidates if s.timestamp.date() == target]
        if exact:
            # Prefer latest snapshot on the exact target day.
            return max(exact, key=lambda s: s.timestamp)

        def _distance(snapshot: DashboardStatSnapshot) -> tuple:
            snap_day = snapshot.timestamp.date()
            day_delta = abs((snap_day - target).days)
            # Closer calendar day first; on tie prefer earlier timestamp of that day.
            return (day_delta, snapshot.timestamp)

        return min(candidates, key=_distance)

    def _wrap_metric(
        self,
        key: str,
        current_metrics: Dict[str, Union[int, float]],
        historical: Optional[DashboardStatSnapshot],
    ) -> MetricWithTrend:
        current = current_metrics.get(key, 0)
        previous = getattr(historical, key, None) if historical is not None else None
        change = calculate_trend_change(current, previous)
        return {"value": current, "trend": format_trend(change)}

    def get_dashboard_stats(self) -> DashboardStatsDict:
        """Get dashboard statistics with nested MoM trends for bento cards."""
        current_metrics = self.collect_current_metrics()

        # Idempotent daily snapshot for future comparisons.
        try:
            self.create_daily_snapshot(metrics=current_metrics)
        except Exception:
            # Dashboard must still render if snapshot write fails.
            db.session.rollback()

        historical = self.get_historical_snapshot(days_ago=30, window_days=3)

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

        return {
            "total_properties": self._wrap_metric(
                "total_properties", current_metrics, historical
            ),
            "active_properties": int(current_metrics["active_properties"]),
            "total_agents": int(current_metrics["total_agents"]),
            "total_customers": self._wrap_metric(
                "total_customers", current_metrics, historical
            ),
            "total_deals": int(current_metrics["total_deals"]),
            "active_deals": self._wrap_metric(
                "active_deals", current_metrics, historical
            ),
            "total_deal_value": self._wrap_metric(
                "total_deal_value", current_metrics, historical
            ),
            "active_deal_value": float(current_metrics["active_deal_value"]),
            "avg_property_price": float(current_metrics["avg_property_price"]),
            "recent_properties": recent_properties,
            "recent_deals": recent_deals,
            "median_price_trend": self._calculate_median_price_trend(),
            "avg_days_on_market_trend": self._calculate_avg_days_on_market_trend(),
            "months_of_supply_trend": self._calculate_months_of_supply_trend(),
            "price_per_sqft_trend": self._calculate_price_per_sqft_trend(),
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
