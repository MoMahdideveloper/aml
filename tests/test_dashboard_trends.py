"""Unit and integration tests for dynamic dashboard MoM trends."""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import inspect

from repositories.dashboard_statistics_repository import (
    DashboardStatisticsRepository,
    TREND_METRIC_KEYS,
    calculate_trend_change,
    format_trend,
)
from sqlalchemy_models import DashboardStatSnapshot


class TestTrendMath:
    def test_positive_change(self):
        assert calculate_trend_change(120, 100) == pytest.approx(20.0)

    def test_negative_change(self):
        assert calculate_trend_change(80, 100) == pytest.approx(-20.0)

    def test_unchanged(self):
        assert calculate_trend_change(50, 50) == pytest.approx(0.0)

    def test_missing_previous(self):
        assert calculate_trend_change(10, None) is None

    def test_missing_current(self):
        assert calculate_trend_change(None, 10) is None

    def test_zero_previous_is_neutral(self):
        assert calculate_trend_change(25, 0) == 0.0
        assert calculate_trend_change(0, 0) == 0.0

    def test_format_up(self):
        trend = format_trend(12.5)
        assert trend["direction"] == "up"
        assert trend["icon"] == "trending_up"
        assert trend["sign"] == "+"
        assert trend["percent"] == "12.5"

    def test_format_down(self):
        trend = format_trend(-5.2)
        assert trend["direction"] == "down"
        assert trend["icon"] == "trending_down"
        assert trend["sign"] == "-"
        assert trend["percent"] == "5.2"

    def test_format_neutral_and_missing(self):
        for change in (None, 0.0, 0.01):
            trend = format_trend(change)
            assert trend["direction"] == "neutral"
            assert trend["icon"] == "trending_flat"
            assert trend["percent"] == "0.0"
            assert trend["sign"] == ""


class TestSnapshotLifecycle:
    def test_schema_has_dashboard_stat_snapshots(self, app, db_setup):
        with app.app_context():
            table_names = inspect(db_setup.engine).get_table_names()
            assert "dashboard_stat_snapshots" in table_names
            columns = {c["name"] for c in inspect(db_setup.engine).get_columns(
                "dashboard_stat_snapshots"
            )}
            expected = {
                "id",
                "timestamp",
                "total_properties",
                "active_properties",
                "total_agents",
                "total_customers",
                "total_deals",
                "active_deals",
                "total_deal_value",
                "active_deal_value",
                "avg_property_price",
                "recent_properties_count",
                "recent_deals_count",
            }
            assert expected.issubset(columns)

    def test_create_daily_snapshot_idempotent(self, app, db_setup):
        with app.app_context():
            repo = DashboardStatisticsRepository()
            metrics = {
                "total_properties": 10,
                "active_properties": 5,
                "total_agents": 2,
                "total_customers": 8,
                "total_deals": 4,
                "active_deals": 3,
                "total_deal_value": 1000,
                "active_deal_value": 500,
                "avg_property_price": 250,
                "recent_properties_count": 2,
                "recent_deals_count": 1,
            }
            first = repo.create_daily_snapshot(metrics=metrics)
            second = repo.create_daily_snapshot(metrics={**metrics, "total_properties": 99})
            assert first.id == second.id
            assert second.total_properties == 10
            assert DashboardStatSnapshot.query.count() == 1

    def test_historical_exact_match_preferred(self, app, db_setup):
        with app.app_context():
            repo = DashboardStatisticsRepository()
            ref = date(2026, 7, 10)
            exact_day = ref - timedelta(days=30)
            nearby = exact_day + timedelta(days=1)

            exact = DashboardStatSnapshot(
                timestamp=datetime.combine(exact_day, datetime.min.time()),
                total_properties=100,
            )
            near = DashboardStatSnapshot(
                timestamp=datetime.combine(nearby, datetime.min.time()),
                total_properties=50,
            )
            db_setup.session.add_all([exact, near])
            db_setup.session.commit()

            found = repo.get_historical_snapshot(
                days_ago=30, window_days=3, reference_date=ref
            )
            assert found is not None
            assert found.id == exact.id
            assert found.total_properties == 100

    def test_historical_closest_within_window(self, app, db_setup):
        with app.app_context():
            repo = DashboardStatisticsRepository()
            ref = date(2026, 7, 10)
            target = ref - timedelta(days=30)
            closer = target + timedelta(days=1)
            farther = target - timedelta(days=2)

            snap_close = DashboardStatSnapshot(
                timestamp=datetime.combine(closer, datetime.min.time()),
                total_properties=11,
            )
            snap_far = DashboardStatSnapshot(
                timestamp=datetime.combine(farther, datetime.min.time()),
                total_properties=22,
            )
            db_setup.session.add_all([snap_close, snap_far])
            db_setup.session.commit()

            found = repo.get_historical_snapshot(
                days_ago=30, window_days=3, reference_date=ref
            )
            assert found is not None
            assert found.total_properties == 11

    def test_historical_outside_window_returns_none(self, app, db_setup):
        with app.app_context():
            repo = DashboardStatisticsRepository()
            ref = date(2026, 7, 10)
            far = ref - timedelta(days=40)
            db_setup.session.add(
                DashboardStatSnapshot(
                    timestamp=datetime.combine(far, datetime.min.time()),
                    total_properties=7,
                )
            )
            db_setup.session.commit()

            found = repo.get_historical_snapshot(
                days_ago=30, window_days=3, reference_date=ref
            )
            assert found is None


class TestGetDashboardStatsTrends:
    def test_nested_trend_metrics_without_history(self, app, db_setup):
        with app.app_context():
            repo = DashboardStatisticsRepository()
            stats = repo.get_dashboard_stats()

            for key in TREND_METRIC_KEYS:
                metric = stats[key]
                assert isinstance(metric, dict)
                assert "value" in metric
                assert "trend" in metric
                assert metric["trend"]["direction"] == "neutral"
                assert metric["trend"]["percent"] == "0.0"

            assert "recent_properties" in stats
            assert "recent_deals" in stats
            assert "median_price_trend" in stats
            # Today's snapshot created
            assert DashboardStatSnapshot.query.count() == 1

    def test_positive_and_negative_trends_from_history(self, app, db_setup):
        with app.app_context():
            from sqlalchemy_models import Agent, Customer, Deal, Property

            agent = Agent(name="Trend Agent", email="trend@example.com", phone="1")
            db_setup.session.add(agent)
            db_setup.session.flush()

            for i in range(4):
                db_setup.session.add(
                    Property(
                        title=f"P{i}",
                        address=f"{i} St",
                        price=100000 + i,
                        property_type="house",
                        bedrooms=3,
                        bathrooms=2,
                        square_feet=1000,
                        description="x",
                        agent_id=agent.id,
                        status="active",
                    )
                )
            for i in range(2):
                db_setup.session.add(
                    Customer(
                        name=f"C{i}",
                        email=f"c{i}@example.com",
                        phone=str(i),
                        status="active",
                    )
                )
            db_setup.session.flush()
            customers = Customer.query.all()
            props = Property.query.all()
            for i in range(2):
                db_setup.session.add(
                    Deal(
                        property_id=props[i].id,
                        customer_id=customers[i % len(customers)].id,
                        agent_id=agent.id,
                        offer_amount=50000,
                        status="prospecting",
                    )
                )
            db_setup.session.commit()

            past = datetime.utcnow() - timedelta(days=30)
            db_setup.session.add(
                DashboardStatSnapshot(
                    timestamp=past,
                    total_properties=2,
                    active_deals=4,
                    total_deal_value=200000,
                    total_customers=4,
                )
            )
            db_setup.session.commit()

            repo = DashboardStatisticsRepository()
            stats = repo.get_dashboard_stats()

            # properties: 4 vs 2 → +100%
            assert stats["total_properties"]["value"] == 4
            assert stats["total_properties"]["trend"]["direction"] == "up"
            assert stats["total_properties"]["trend"]["percent"] == "100.0"

            # active deals: 2 vs 4 → -50%
            assert stats["active_deals"]["value"] == 2
            assert stats["active_deals"]["trend"]["direction"] == "down"
            assert stats["active_deals"]["trend"]["sign"] == "-"
            assert stats["active_deals"]["trend"]["percent"] == "50.0"

    def test_dashboard_route_renders_trend_text(self, client, app, db_setup):
        with app.app_context():
            past = datetime.utcnow() - timedelta(days=30)
            db_setup.session.add(
                DashboardStatSnapshot(
                    timestamp=past,
                    total_properties=1,
                    active_deals=1,
                    total_deal_value=1,
                    total_customers=1,
                )
            )
            db_setup.session.commit()

            response = client.get("/dashboard")
            assert response.status_code == 200
            text = response.data.decode("utf-8")
            assert "vs last month" in text
            assert "Total Properties" in text
            assert "Active Deals" in text
            assert "Monthly Revenue" in text
            assert "Total Clients" in text
            # Neutral (all zeros vs history of 1) or any computed percent
            assert "%" in text
