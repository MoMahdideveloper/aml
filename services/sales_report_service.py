"""Sales reporting: pipeline, forecast, funnel, agent metrics, export."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import and_, func

from database import db
from services.deal_pipeline import (
    ALL_STAGES,
    LOST_STAGE,
    OPEN_STAGES,
    WON_STAGE,
    is_open_stage,
    normalize_deal_status,
    stage_probability,
)
from services.import_parser import write_safe_csv
from sqlalchemy_models import Agent, Deal, DealStageHistory, ForecastSnapshot, Task, _utcnow_naive
from utils.observability import log_event, record_business_counter


class ReportValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def feature_enabled() -> bool:
    return os.environ.get("ENABLE_SALES_REPORTS", "1").strip() != "0"


def _d(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(int(v))


def _money(v: Any) -> int:
    if not isinstance(v, Decimal):
        v = Decimal(str(v or 0))
    return int(v.to_integral_value(rounding=ROUND_HALF_UP))


def _pct(num: int, den: int) -> Optional[float]:
    if den <= 0:
        return None
    return round(100.0 * num / den, 2)


def _pct_change(cur: Decimal, prior: Decimal) -> Optional[float]:
    if prior == 0:
        if cur == 0:
            return 0.0
        return None  # neutral / undefined
    return round(float((cur - prior) / prior * 100), 2)


@dataclass
class ReportFilters:
    start: datetime
    end: datetime  # exclusive
    agent_ids: Optional[List[int]] = None
    stages: Optional[List[str]] = None
    listing_type: Optional[str] = None
    actor_id: Optional[int] = None
    actor_role: str = "agent"

    @property
    def prior_start(self) -> datetime:
        delta = self.end - self.start
        return self.start - delta

    @property
    def prior_end(self) -> datetime:
        return self.start

    def scope_key(self) -> str:
        agents = ",".join(str(a) for a in sorted(self.agent_ids or [])) or "all"
        return f"agents={agents}|{self.start.date()}|{self.end.date()}"


def parse_report_filters(
    *,
    start: Optional[str],
    end: Optional[str],
    agent_id: Optional[str] = None,
    days: Optional[str] = None,
    actor_id: Optional[int] = None,
    actor_role: str = "agent",
) -> ReportFilters:
    now = _utcnow_naive()
    # default last 30 days
    try:
        d = int(days) if days else 30
    except ValueError:
        raise ReportValidationError("bad_days", "Invalid days") from None
    d = max(1, min(d, 366))

    if end:
        try:
            end_dt = datetime.fromisoformat(end.replace("Z", ""))
        except ValueError:
            raise ReportValidationError("bad_end", "Invalid end date") from None
    else:
        end_dt = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    if start:
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", ""))
        except ValueError:
            raise ReportValidationError("bad_start", "Invalid start date") from None
    else:
        start_dt = end_dt - timedelta(days=d)

    if start_dt >= end_dt:
        raise ReportValidationError("bad_period", "start must be before end")

    agent_ids = None
    if agent_id not in (None, "", "all"):
        try:
            agent_ids = [int(agent_id)]
        except ValueError:
            raise ReportValidationError("bad_agent", "Invalid agent_id") from None

    return ReportFilters(
        start=start_dt,
        end=end_dt,
        agent_ids=agent_ids,
        actor_id=actor_id,
        actor_role=(actor_role or "agent").lower(),
    )


class SalesReportService:
    def build_report(self, filters: ReportFilters) -> Dict[str, Any]:
        t0 = time.perf_counter()
        current = self._period_metrics(filters.start, filters.end, filters.agent_ids)
        prior = self._period_metrics(filters.prior_start, filters.prior_end, filters.agent_ids)
        funnel = self._funnel(filters.agent_ids)
        agents = self._agent_rows(filters)
        comparison = {
            k: {
                "current": current[k],
                "prior": prior[k],
                "delta": self._delta(current[k], prior[k]),
                "pct_change": self._delta_pct(current[k], prior[k]),
            }
            for k in (
                "pipeline_value",
                "weighted_forecast",
                "won_value",
                "lost_value",
                "won_count",
                "lost_count",
                "win_rate",
                "avg_deal_size",
            )
        }
        duration_ms = int((time.perf_counter() - t0) * 1000)
        log_event(
            "sales_report_generated",
            component="reports",
            duration_ms=duration_ms,
            agent_filter=bool(filters.agent_ids),
            # no raw filter text / names
        )
        record_business_counter("crm_reports_total", outcome="ok")
        engagement = {}
        try:
            from services.customer_timeline_service import customer_timeline_service

            engagement = customer_timeline_service.engagement_metrics(
                start=filters.start,
                end=filters.end,
                agent_ids=filters.agent_ids,
                inactive_days=14,
            )
        except Exception:
            engagement = {}

        return {
            "generated_at": _utcnow_naive().isoformat() + "Z",
            "period": {
                "start": filters.start.isoformat(),
                "end": filters.end.isoformat(),
                "prior_start": filters.prior_start.isoformat(),
                "prior_end": filters.prior_end.isoformat(),
            },
            "summary": current,
            "comparison": comparison,
            "funnel": funnel,
            "agents": agents,
            "engagement": engagement,
            "probabilities": {k: float(stage_probability(k)) for k in OPEN_STAGES},
            "limitations": {
                "stage_conversion_requires_observed_history": True,
                "baseline_history_excluded_from_conversion": True,
                "sales_cycle_uses_history_or_updated_proxy": True,
                "engagement_excludes_note_bodies": True,
            },
        }

    def _delta(self, cur: Any, prior: Any) -> Any:
        if cur is None or prior is None:
            return None
        if isinstance(cur, (int, float)) and isinstance(prior, (int, float)):
            return cur - prior
        return None

    def _delta_pct(self, cur: Any, prior: Any) -> Optional[float]:
        if cur is None or prior is None:
            return None
        try:
            return _pct_change(Decimal(str(cur)), Decimal(str(prior)))
        except Exception:
            return None

    def _deal_q(self, agent_ids: Optional[List[int]] = None):
        q = Deal.query.filter(Deal.is_deleted.is_(False))
        if agent_ids:
            q = q.filter(Deal.agent_id.in_(agent_ids))
        return q

    def _period_metrics(
        self, start: datetime, end: datetime, agent_ids: Optional[List[int]]
    ) -> Dict[str, Any]:
        deals = self._deal_q(agent_ids).all()
        open_deals = [d for d in deals if is_open_stage(d.status)]
        pipeline_value = sum((_d(d.offer_amount) for d in open_deals), Decimal("0"))
        weighted = sum(
            (_d(d.offer_amount) * stage_probability(d.status) for d in open_deals),
            Decimal("0"),
        )

        # Terminal outcomes in period: prefer history transitions into won/lost
        won_ids, lost_ids = self._terminal_in_period(start, end, agent_ids)
        deal_map = {d.id: d for d in deals}
        won_deals = [deal_map[i] for i in won_ids if i in deal_map]
        lost_deals = [deal_map[i] for i in lost_ids if i in deal_map]

        # Fallback: status terminal and updated_at in period if no history
        if not won_ids and not lost_ids:
            for d in deals:
                st = normalize_deal_status(d.status)
                ua = d.updated_at or d.created_at
                if not ua or not (start <= ua < end):
                    continue
                if st == WON_STAGE:
                    won_deals.append(d)
                elif st == LOST_STAGE:
                    lost_deals.append(d)

        won_value = sum((_d(d.offer_amount) for d in won_deals), Decimal("0"))
        lost_value = sum((_d(d.offer_amount) for d in lost_deals), Decimal("0"))
        won_count = len(won_deals)
        lost_count = len(lost_deals)
        closed = won_count + lost_count
        win_rate = _pct(won_count, closed)
        avg_size = (
            float(won_value / won_count) if won_count else None
        )

        cycles = []
        for d in won_deals:
            won_at = self._won_at(d.id) or d.updated_at
            if d.created_at and won_at:
                cycles.append((won_at - d.created_at).total_seconds() / 86400.0)
        avg_cycle = round(sum(cycles) / len(cycles), 2) if cycles else None

        return {
            "open_count": len(open_deals),
            "pipeline_value": _money(pipeline_value),
            "weighted_forecast": _money(weighted),
            "won_count": won_count,
            "lost_count": lost_count,
            "won_value": _money(won_value),
            "lost_value": _money(lost_value),
            "win_rate": win_rate,
            "avg_deal_size": int(avg_size) if avg_size is not None else None,
            "avg_sales_cycle_days": avg_cycle,
        }

    def _terminal_in_period(
        self, start: datetime, end: datetime, agent_ids: Optional[List[int]]
    ) -> Tuple[List[int], List[int]]:
        q = DealStageHistory.query.filter(
            DealStageHistory.event_type == "transition",
            DealStageHistory.changed_at >= start,
            DealStageHistory.changed_at < end,
            DealStageHistory.to_stage.in_([WON_STAGE, LOST_STAGE]),
        )
        rows = q.all()
        won, lost = [], []
        for r in rows:
            deal = db.session.get(Deal, r.deal_id)
            if not deal or deal.is_deleted:
                continue
            if agent_ids and deal.agent_id not in agent_ids:
                continue
            if r.to_stage == WON_STAGE:
                won.append(r.deal_id)
            elif r.to_stage == LOST_STAGE:
                lost.append(r.deal_id)
        return won, lost

    def _won_at(self, deal_id: int) -> Optional[datetime]:
        row = (
            DealStageHistory.query.filter_by(
                deal_id=deal_id, to_stage=WON_STAGE, event_type="transition"
            )
            .order_by(DealStageHistory.changed_at.desc())
            .first()
        )
        return row.changed_at if row else None

    def _funnel(self, agent_ids: Optional[List[int]]) -> List[Dict[str, Any]]:
        deals = self._deal_q(agent_ids).all()
        by_stage: Dict[str, List[Deal]] = {s: [] for s in ALL_STAGES}
        for d in deals:
            st = normalize_deal_status(d.status)
            by_stage.setdefault(st, []).append(d)

        # Observed conversion: entries to stage / forward exits (exclude baseline)
        hist = DealStageHistory.query.filter(
            DealStageHistory.event_type == "transition"
        ).all()
        entries: Dict[str, int] = {s: 0 for s in ALL_STAGES}
        forward_exits: Dict[str, int] = {s: 0 for s in ALL_STAGES}
        for h in hist:
            to_s = normalize_deal_status(h.to_stage)
            from_s = normalize_deal_status(h.from_stage) if h.from_stage else ""
            entries[to_s] = entries.get(to_s, 0) + 1
            if from_s and from_s in OPEN_STAGES:
                from services.deal_pipeline import is_forward_transition

                if is_forward_transition(from_s, to_s):
                    forward_exits[from_s] = forward_exits.get(from_s, 0) + 1

        rows = []
        for stage in ALL_STAGES:
            bucket = by_stage.get(stage) or []
            value = sum((_d(d.offer_amount) for d in bucket), Decimal("0"))
            ent = entries.get(stage, 0)
            exits = forward_exits.get(stage, 0)
            conv = _pct(exits, ent) if stage in OPEN_STAGES else None
            rows.append(
                {
                    "stage": stage,
                    "label": stage.replace("_", " ").title(),
                    "count": len(bucket),
                    "value": _money(value),
                    "probability": float(stage_probability(stage)),
                    "weighted": _money(
                        sum(
                            (
                                _d(d.offer_amount) * stage_probability(stage)
                                for d in bucket
                            ),
                            Decimal("0"),
                        )
                    ),
                    "observed_entries": ent,
                    "forward_exits": exits,
                    "stage_conversion_pct": conv,
                    "conversion_note": "observed history only; baseline excluded",
                }
            )
        return rows

    def _agent_rows(self, filters: ReportFilters) -> List[Dict[str, Any]]:
        agents = Agent.query.filter(Agent.is_deleted.is_(False)).order_by(Agent.id).all()
        if filters.agent_ids:
            agents = [a for a in agents if a.id in filters.agent_ids]
        rows = []
        for a in agents:
            m = self._period_metrics(filters.start, filters.end, [a.id])
            open_m = self._period_metrics(
                filters.start - timedelta(days=3650), filters.end, [a.id]
            )
            # overdue tasks
            now = _utcnow_naive()
            overdue = (
                Task.query.filter(
                    Task.is_deleted.is_(False),
                    Task.agent_id == a.id,
                    Task.status != "completed",
                    Task.due_date.isnot(None),
                    Task.due_date < now,
                ).count()
            )
            rows.append(
                {
                    "agent_id": a.id,
                    "agent_name": a.name,
                    "pipeline_value": open_m["pipeline_value"],
                    "weighted_forecast": open_m["weighted_forecast"],
                    "won_value": m["won_value"],
                    "won_count": m["won_count"],
                    "win_rate": m["win_rate"],
                    "avg_deal_size": m["avg_deal_size"],
                    "avg_sales_cycle_days": m["avg_sales_cycle_days"],
                    "overdue_tasks": overdue,
                }
            )
        return rows

    def export_csv(self, filters: ReportFilters, max_rows: int = 5000) -> str:
        report = self.build_report(filters)
        headers = [
            "section",
            "key",
            "value",
            "period_start",
            "period_end",
            "generated_at",
        ]
        rows: List[List[Any]] = []
        meta = report["period"]
        gen = report["generated_at"]
        for k, v in report["summary"].items():
            rows.append(["summary", k, v, meta["start"], meta["end"], gen])
        for f in report["funnel"]:
            rows.append(
                [
                    "funnel",
                    f["stage"],
                    f"{f['count']}|{f['value']}|{f['weighted']}",
                    meta["start"],
                    meta["end"],
                    gen,
                ]
            )
        for a in report["agents"][: max(0, max_rows - len(rows))]:
            rows.append(
                [
                    "agent",
                    a["agent_name"],
                    f"won={a['won_value']}|pipe={a['pipeline_value']}|wr={a['win_rate']}",
                    meta["start"],
                    meta["end"],
                    gen,
                ]
            )
        log_event("sales_report_export", component="reports", row_count=len(rows))
        return write_safe_csv(headers, rows)

    def snapshot_forecast(self, filters: ReportFilters) -> ForecastSnapshot:
        """Idempotent snapshot for scope/period."""
        scope = filters.scope_key()
        existing = ForecastSnapshot.query.filter_by(
            scope_key=scope,
            period_start=filters.start,
            period_end=filters.end,
        ).first()
        summary = self._period_metrics(filters.start, filters.end, filters.agent_ids)
        # use open pipeline metrics from current open set
        deals = self._deal_q(filters.agent_ids).all()
        open_deals = [d for d in deals if is_open_stage(d.status)]
        pipe = _money(sum((_d(d.offer_amount) for d in open_deals), Decimal("0")))
        weighted = _money(
            sum(
                (
                    _d(d.offer_amount) * stage_probability(d.status)
                    for d in open_deals
                ),
                Decimal("0"),
            )
        )
        if existing:
            existing.weighted_forecast = weighted
            existing.open_pipeline = pipe
            existing.open_count = len(open_deals)
            existing.as_of = _utcnow_naive()
            db.session.commit()
            return existing
        snap = ForecastSnapshot(
            scope_key=scope,
            period_start=filters.start,
            period_end=filters.end,
            as_of=_utcnow_naive(),
            weighted_forecast=weighted,
            open_pipeline=pipe,
            open_count=len(open_deals),
            agent_id=(filters.agent_ids[0] if filters.agent_ids else None),
        )
        db.session.add(snap)
        db.session.commit()
        return snap

    def forecast_accuracy(
        self, filters: ReportFilters
    ) -> Dict[str, Any]:
        """Compare snapshot weighted forecast to won value in period (if closed)."""
        now = _utcnow_naive()
        if filters.end > now:
            return {
                "status": "incomplete_period",
                "message": "Accuracy available only after period end",
            }
        snap = ForecastSnapshot.query.filter_by(
            scope_key=filters.scope_key(),
            period_start=filters.start,
            period_end=filters.end,
        ).first()
        if not snap:
            return {"status": "no_snapshot", "message": "No forecast snapshot for scope"}
        m = self._period_metrics(filters.start, filters.end, filters.agent_ids)
        forecast = snap.weighted_forecast
        actual = m["won_value"]
        if forecast == 0:
            err_pct = None if actual == 0 else None
        else:
            err_pct = round(100.0 * (actual - forecast) / forecast, 2)
        return {
            "status": "ok",
            "forecast": forecast,
            "actual_won_value": actual,
            "error_pct": err_pct,
            "sample_won_count": m["won_count"],
            "low_sample": m["won_count"] < 3,
        }


sales_report_service = SalesReportService()
