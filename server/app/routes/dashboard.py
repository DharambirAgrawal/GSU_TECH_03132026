from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from flask import Blueprint, jsonify, request
from sqlalchemy import desc, func

from app.models.simulation import (
    Citation,
    Error,
    FactCheck,
    Prompt,
    PromptModelRun,
    ReportSummary,
    Simulation,
)
from app.services.auth_service import require_company_session

bp = Blueprint("dashboard", __name__)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _normalize_domain(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = parsed.hostname or text
    return host.removeprefix("www.").lower()


def _as_json_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
            return loaded if isinstance(loaded, list) else []
        except Exception:
            return []
    return []


def _empty_payload(company) -> dict:
    return {
        "success": True,
        "has_data": False,
        "company": {
            "id": company.id,
            "name": company.name,
            "slug": company.slug,
            "approved_email_domain": company.approved_email_domain,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_simulations": 0,
            "total_prompts": 0,
            "total_model_runs": 0,
            "total_citations": 0,
            "total_errors": 0,
            "avg_fact_score": 0.0,
            "dead_links_count": 0,
            "hallucination_count": 0,
            "last_simulation_status": None,
            "last_simulation_completed_at": None,
        },
        "cards": {
            "accuracy_score": 0,
            "visibility_score": 0,
            "competitors_tracked": 0,
            "action_items": 0,
        },
        "visibility": {
            "total_mentions": 0,
            "mentions_by_model": [],
            "recent_mentions": [],
        },
        "accuracy": {
            "overall_score": 0,
            "avg_fact_score": 0.0,
            "dead_links_count": 0,
            "hallucination_count": 0,
            "low_confidence_checks": 0,
            "trend": [],
        },
        "competitors": {
            "tracked_domains": [],
            "top_domains": [],
        },
        "actions": {
            "open_items_count": 0,
            "error_breakdown": [],
            "top_failure_reasons": [],
            "top_mitigations": [],
        },
        "activity": [
            {
                "type": "info",
                "message": "No simulations yet. Create your first simulation to start analytics.",
                "timestamp": None,
            }
        ],
    }


@bp.route("/analytics", methods=["GET"])
def get_dashboard_analytics():
    try:
        _, company = require_company_session(request)
    except PermissionError as exc:
        return jsonify({"success": False, "message": str(exc)}), 401

    simulations = (
        Simulation.query.filter_by(company_id=company.id)
        .order_by(desc(Simulation.time_created))
        .all()
    )

    if not simulations:
        return jsonify(_empty_payload(company)), 200

    simulation_ids = [s.id for s in simulations]

    total_prompts = (
        Prompt.query.with_entities(func.count(Prompt.id))
        .filter(Prompt.simulation_id.in_(simulation_ids))
        .scalar()
        or 0
    )
    total_runs = (
        PromptModelRun.query.with_entities(func.count(PromptModelRun.id))
        .filter(PromptModelRun.simulation_id.in_(simulation_ids))
        .scalar()
        or 0
    )
    total_citations = (
        Citation.query.with_entities(func.count(Citation.id))
        .filter(Citation.simulation_id.in_(simulation_ids))
        .scalar()
        or 0
    )
    total_errors = (
        Error.query.with_entities(func.count(Error.id))
        .filter(Error.simulation_id.in_(simulation_ids))
        .scalar()
        or 0
    )

    avg_fact_score = (
        FactCheck.query.with_entities(func.avg(FactCheck.fact_score))
        .filter(FactCheck.simulation_id.in_(simulation_ids))
        .scalar()
    )
    avg_fact_score = round(float(avg_fact_score), 4) if avg_fact_score is not None else 0.0

    dead_links_count = (
        PromptModelRun.query.with_entities(func.sum(PromptModelRun.dead_links_count))
        .filter(PromptModelRun.simulation_id.in_(simulation_ids))
        .scalar()
        or 0
    )
    hallucination_count = (
        Error.query.with_entities(func.count(Error.id))
        .filter(
            Error.simulation_id.in_(simulation_ids),
            Error.error_type == "hallucination",
        )
        .scalar()
        or 0
    )

    low_confidence_checks = (
        FactCheck.query.with_entities(func.count(FactCheck.id))
        .filter(
            FactCheck.simulation_id.in_(simulation_ids),
            FactCheck.fact_score < 0.35,
        )
        .scalar()
        or 0
    )

    mentions_by_model_rows = (
        Citation.query.with_entities(Citation.model_name, func.count(Citation.id))
        .filter(Citation.simulation_id.in_(simulation_ids))
        .group_by(Citation.model_name)
        .order_by(desc(func.count(Citation.id)))
        .all()
    )
    mentions_by_model = [
        {"model": model_name, "mentions": int(count)}
        for model_name, count in mentions_by_model_rows
    ]

    recent_mentions_rows = (
        Citation.query.with_entities(
            Citation.model_name,
            Citation.company_cited,
            Citation.cited_url,
            Citation.website_domain,
            Citation.time_created,
            Prompt.text,
        )
        .join(Prompt, Prompt.id == Citation.prompt_id)
        .filter(Citation.simulation_id.in_(simulation_ids))
        .order_by(desc(Citation.time_created))
        .limit(8)
        .all()
    )
    recent_mentions = [
        {
            "model": row[0],
            "company_cited": row[1],
            "url": row[2],
            "domain": row[3],
            "timestamp": _iso(row[4]),
            "prompt": row[5],
        }
        for row in recent_mentions_rows
    ]

    company_domain = _normalize_domain(company.primary_domain)
    top_domains_rows = (
        Citation.query.with_entities(Citation.website_domain, func.count(Citation.id))
        .filter(Citation.simulation_id.in_(simulation_ids))
        .group_by(Citation.website_domain)
        .order_by(desc(func.count(Citation.id)))
        .limit(20)
        .all()
    )

    tracked_domains = []
    for domain, count in top_domains_rows:
        clean = (domain or "").removeprefix("www.").lower()
        if not clean or clean == company_domain:
            continue
        tracked_domains.append({"domain": clean, "mentions": int(count)})

    error_breakdown_rows = (
        Error.query.with_entities(Error.error_type, Error.severity, func.count(Error.id))
        .filter(Error.simulation_id.in_(simulation_ids))
        .group_by(Error.error_type, Error.severity)
        .order_by(desc(func.count(Error.id)))
        .all()
    )
    error_breakdown = [
        {"type": row[0], "severity": row[1], "count": int(row[2])}
        for row in error_breakdown_rows
    ]

    trend_start = datetime.now(timezone.utc) - timedelta(days=14)
    trend_rows = (
        FactCheck.query.with_entities(
            func.date(FactCheck.time_created),
            func.avg(FactCheck.fact_score),
            func.count(FactCheck.id),
        )
        .filter(
            FactCheck.simulation_id.in_(simulation_ids),
            FactCheck.time_created >= trend_start,
        )
        .group_by(func.date(FactCheck.time_created))
        .order_by(func.date(FactCheck.time_created))
        .all()
    )
    trend = [
        {
            "date": str(row[0]),
            "avg_fact_score": round(float(row[1]), 4),
            "checks": int(row[2]),
        }
        for row in trend_rows
        if row[1] is not None
    ]

    latest_simulation = simulations[0]
    latest_summary = (
        ReportSummary.query.join(Simulation, Simulation.id == ReportSummary.simulation_id)
        .filter(Simulation.company_id == company.id)
        .order_by(desc(ReportSummary.generated_at))
        .first()
    )

    top_failure_reasons = _as_json_list(latest_summary.top_failure_reasons) if latest_summary else []
    top_mitigations = _as_json_list(latest_summary.top_mitigations) if latest_summary else []

    if not top_mitigations:
        mitigation_rows = (
            Error.query.with_entities(Error.mitigation, func.count(Error.id))
            .filter(Error.simulation_id.in_(simulation_ids), Error.mitigation.isnot(None))
            .group_by(Error.mitigation)
            .order_by(desc(func.count(Error.id)))
            .limit(5)
            .all()
        )
        top_mitigations = [
            {"mitigation": row[0], "count": int(row[1])}
            for row in mitigation_rows
            if row[0]
        ]

    if not top_failure_reasons:
        failure_rows = (
            Error.query.with_entities(Error.reason_for_failure, func.count(Error.id))
            .filter(Error.simulation_id.in_(simulation_ids), Error.reason_for_failure.isnot(None))
            .group_by(Error.reason_for_failure)
            .order_by(desc(func.count(Error.id)))
            .limit(5)
            .all()
        )
        top_failure_reasons = [
            {"reason": row[0], "count": int(row[1])}
            for row in failure_rows
            if row[0]
        ]

    action_items = sum(
        item["count"]
        for item in error_breakdown
        if item["severity"] in {"high", "critical"}
    )

    activity = [
        {
            "type": "simulation",
            "message": f"Latest simulation is {latest_simulation.status}",
            "timestamp": _iso(latest_simulation.time_ended or latest_simulation.time_started),
        }
    ]
    if recent_mentions:
        top_recent = recent_mentions[0]
        activity.append(
            {
                "type": "mention",
                "message": f"{top_recent['model']} cited {top_recent['domain']}",
                "timestamp": top_recent["timestamp"],
            }
        )
    if error_breakdown:
        top_error = error_breakdown[0]
        activity.append(
            {
                "type": "error",
                "message": f"Top issue: {top_error['type']} ({top_error['count']})",
                "timestamp": _iso(datetime.now(timezone.utc)),
            }
        )

    visibility_score = round(min(100.0, (total_citations / max(total_runs, 1)) * 100), 2)
    accuracy_score = round(company.accuracy_score or (avg_fact_score * 100), 2)

    payload = {
        "success": True,
        "has_data": total_runs > 0,
        "company": {
            "id": company.id,
            "name": company.name,
            "slug": company.slug,
            "approved_email_domain": company.approved_email_domain,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_simulations": len(simulations),
            "total_prompts": int(total_prompts),
            "total_model_runs": int(total_runs),
            "total_citations": int(total_citations),
            "total_errors": int(total_errors),
            "avg_fact_score": avg_fact_score,
            "dead_links_count": int(dead_links_count),
            "hallucination_count": int(hallucination_count),
            "last_simulation_status": latest_simulation.status,
            "last_simulation_completed_at": _iso(latest_simulation.time_ended),
        },
        "cards": {
            "accuracy_score": accuracy_score,
            "visibility_score": round(company.ai_visibility_score or visibility_score, 2),
            "competitors_tracked": len(tracked_domains),
            "action_items": int(action_items),
        },
        "visibility": {
            "total_mentions": int(total_citations),
            "mentions_by_model": mentions_by_model,
            "recent_mentions": recent_mentions,
        },
        "accuracy": {
            "overall_score": accuracy_score,
            "avg_fact_score": avg_fact_score,
            "dead_links_count": int(dead_links_count),
            "hallucination_count": int(hallucination_count),
            "low_confidence_checks": int(low_confidence_checks),
            "trend": trend,
        },
        "competitors": {
            "tracked_domains": tracked_domains,
            "top_domains": tracked_domains[:10],
        },
        "actions": {
            "open_items_count": int(action_items),
            "error_breakdown": error_breakdown,
            "top_failure_reasons": top_failure_reasons,
            "top_mitigations": top_mitigations,
        },
        "activity": activity,
    }

    return jsonify(payload), 200
