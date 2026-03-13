"""
API routes for dashboard metrics: accuracy, visibility, competitors, actions.
All endpoints require authentication via company session.
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import func, desc

from app.extensions import db
from app.models.simulation import (
    Simulation,
    Prompt,
    PromptModelRun,
    Citation,
    Error,
    FactCheck,
    ReportSummary,
)
from app.services.auth_service import require_company_session

bp = Blueprint("metrics", __name__)


# ─────────────────────────────────────────────
# Dashboard Overview Stats
# ─────────────────────────────────────────────
@bp.route("/dashboard", methods=["GET"])
def get_dashboard_stats():
    """Get overview stats for dashboard: accuracy, visibility, competitors, actions."""
    try:
        user, company = require_company_session(request)
    except PermissionError as exc:
        return jsonify({"success": False, "message": str(exc)}), 401

    # Get all simulations for this company
    simulations = Simulation.query.filter_by(company_id=company.id).all()
    sim_ids = [s.id for s in simulations]

    if not sim_ids:
        return jsonify({
            "success": True,
            "data": {
                "accuracy": {"score": 0, "change": 0, "totalChecks": 0},
                "visibility": {"mentions": 0, "change": 0, "platforms": []},
                "competitors": {"total": 0, "yourRank": None, "topCompetitor": None},
                "actions": {"errorCount": 0, "criticalCount": 0},
                "recentActivity": [],
            }
        }), 200

    # --- Accuracy metrics ---
    fact_checks = FactCheck.query.filter(
        FactCheck.simulation_id.in_(sim_ids)).all()
    avg_fact_score = (
        sum(fc.fact_score for fc in fact_checks) / len(fact_checks) * 100
        if fact_checks else 0
    )

    # --- Visibility metrics (total citations = mentions) ---
    citations = Citation.query.filter(
        Citation.simulation_id.in_(sim_ids)).all()
    total_mentions = len(citations)

    # Group citations by model (platform)
    platform_counts = {}
    for c in citations:
        model = c.model_name or "Unknown"
        platform_counts[model] = platform_counts.get(model, 0) + 1
    platforms = [{"name": k, "mentions": v} for k, v in sorted(
        platform_counts.items(), key=lambda x: -x[1]
    )[:5]]

    # --- Competitor metrics (companies cited) ---
    competitor_counts = {}
    company_domain = company.primary_domain or ""
    for c in citations:
        cited = c.company_cited or c.website_domain
        if cited and cited.lower() != company_domain.lower():
            competitor_counts[cited] = competitor_counts.get(cited, 0) + 1

    sorted_competitors = sorted(competitor_counts.items(), key=lambda x: -x[1])
    top_competitor = sorted_competitors[0][0] if sorted_competitors else None
    total_competitors = len(sorted_competitors)

    # Your rank among cited domains
    your_mentions = sum(
        1 for c in citations
        if (c.company_cited or c.website_domain or "").lower() == company_domain.lower()
    )
    all_ranks = [(company_domain, your_mentions)] + list(sorted_competitors)
    all_ranks_sorted = sorted(all_ranks, key=lambda x: -x[1])
    your_rank = next(
        (i + 1 for i, r in enumerate(all_ranks_sorted)
         if r[0].lower() == company_domain.lower()),
        None
    )

    # --- Actions / Errors ---
    errors = Error.query.filter(Error.simulation_id.in_(sim_ids)).all()
    error_count = len(errors)
    critical_count = sum(1 for e in errors if e.severity == "critical")

    # --- Recent Activity ---
    recent_sims = Simulation.query.filter_by(company_id=company.id)\
        .order_by(desc(Simulation.time_created)).limit(5).all()
    recent_activity = [
        {
            "type": "simulation",
            "status": s.status,
            "product": s.product_specification[:50] if s.product_specification else "Simulation",
            "time": s.time_created.isoformat() if s.time_created else None,
        }
        for s in recent_sims
    ]

    return jsonify({
        "success": True,
        "data": {
            "accuracy": {
                "score": round(avg_fact_score, 1),
                "change": 0,  # TODO: calculate trend
                "totalChecks": len(fact_checks),
            },
            "visibility": {
                "mentions": total_mentions,
                "change": 0,  # TODO: calculate trend
                "platforms": platforms,
            },
            "competitors": {
                "total": total_competitors,
                "yourRank": your_rank,
                "topCompetitor": top_competitor,
            },
            "actions": {
                "errorCount": error_count,
                "criticalCount": critical_count,
            },
            "recentActivity": recent_activity,
        }
    }), 200


# ─────────────────────────────────────────────
# Accuracy Page - Detailed fact check data
# ─────────────────────────────────────────────
@bp.route("/accuracy", methods=["GET"])
def get_accuracy_details():
    """Get detailed accuracy/fact-check data."""
    try:
        user, company = require_company_session(request)
    except PermissionError as exc:
        return jsonify({"success": False, "message": str(exc)}), 401

    sim_ids = [s.id for s in Simulation.query.filter_by(
        company_id=company.id).all()]

    if not sim_ids:
        return jsonify({
            "success": True,
            "data": {"percent": 0, "reasons": [], "history": [], "factChecks": []}
        }), 200

    fact_checks = FactCheck.query.filter(FactCheck.simulation_id.in_(sim_ids))\
        .order_by(desc(FactCheck.time_created)).all()

    avg_score = (
        sum(fc.fact_score for fc in fact_checks) / len(fact_checks) * 100
        if fact_checks else 0
    )

    # Get unique reasons (mitigations) for low scores
    reasons = list(set(
        fc.reason_for_score for fc in fact_checks
        if fc.fact_score < 0.8 and fc.reason_for_score
    ))[:5]

    # History by date (aggregate by day)
    date_scores = {}
    for fc in fact_checks:
        date_str = fc.time_created.strftime(
            "%Y-%m-%d") if fc.time_created else "Unknown"
        if date_str not in date_scores:
            date_scores[date_str] = []
        date_scores[date_str].append(fc.fact_score * 100)

    history = [
        {"date": d, "value": round(sum(scores) / len(scores), 1)}
        for d, scores in sorted(date_scores.items())[-10:]
    ]

    # Detailed fact checks
    fact_check_details = [
        {
            "id": fc.id,
            "score": round(fc.fact_score * 100, 1),
            "reason": fc.reason_for_score,
            "mitigation": fc.mitigation,
            "model": fc.model_name,
            "link": fc.company_link,
            "date": fc.time_created.isoformat() if fc.time_created else None,
        }
        for fc in fact_checks[:20]
    ]

    return jsonify({
        "success": True,
        "data": {
            "percent": round(avg_score, 1),
            "reasons": reasons,
            "history": history,
            "factChecks": fact_check_details,
        }
    }), 200


# ─────────────────────────────────────────────
# Visibility Page - Citation and mention data
# ─────────────────────────────────────────────
@bp.route("/visibility", methods=["GET"])
def get_visibility_details():
    """Get visibility data: mentions by platform, sentiment, recent mentions."""
    try:
        user, company = require_company_session(request)
    except PermissionError as exc:
        return jsonify({"success": False, "message": str(exc)}), 401

    sim_ids = [s.id for s in Simulation.query.filter_by(
        company_id=company.id).all()]

    if not sim_ids:
        return jsonify({
            "success": True,
            "data": {
                "totalMentions": 0,
                "platforms": [],
                "sentiment": {"positive": 0, "neutral": 0, "negative": 0},
                "recentMentions": [],
            }
        }), 200

    citations = Citation.query.filter(
        Citation.simulation_id.in_(sim_ids)).all()

    # Platform breakdown
    platform_counts = {}
    for c in citations:
        model = c.model_name or "Unknown"
        platform_counts[model] = platform_counts.get(model, 0) + 1

    platforms = [
        {"name": k, "mentions": v}
        for k, v in sorted(platform_counts.items(), key=lambda x: -x[1])
    ]

    # Get fact checks for sentiment analysis (score-based)
    fact_checks = FactCheck.query.filter(
        FactCheck.simulation_id.in_(sim_ids)).all()
    positive = sum(1 for fc in fact_checks if fc.fact_score >= 0.7)
    neutral = sum(1 for fc in fact_checks if 0.4 <= fc.fact_score < 0.7)
    negative = sum(1 for fc in fact_checks if fc.fact_score < 0.4)

    # Recent mentions (from model runs with company citations)
    recent_runs = PromptModelRun.query.filter(
        PromptModelRun.simulation_id.in_(sim_ids)
    ).order_by(desc(PromptModelRun.time_created)).limit(10).all()

    recent_mentions = []
    for run in recent_runs:
        prompt = Prompt.query.get(run.prompt_id)
        sentiment = "positive" if (run.fact_score or 0) >= 0.7 else (
            "neutral" if (run.fact_score or 0) >= 0.4 else "negative"
        )
        recent_mentions.append({
            "platform": run.model_name,
            "text": prompt.text[:150] if prompt else "Query",
            "date": run.time_created.strftime("%Y-%m-%d") if run.time_created else None,
            "sentiment": sentiment,
        })

    return jsonify({
        "success": True,
        "data": {
            "totalMentions": len(citations),
            "platforms": platforms,
            "sentiment": {
                "positive": positive,
                "neutral": neutral,
                "negative": negative,
            },
            "recentMentions": recent_mentions,
        }
    }), 200


# ─────────────────────────────────────────────
# Competitors Page - Competitor analysis
# ─────────────────────────────────────────────
@bp.route("/competitors", methods=["GET"])
def get_competitors_details():
    """Get competitor analysis: rankings, market share, trends."""
    try:
        user, company = require_company_session(request)
    except PermissionError as exc:
        return jsonify({"success": False, "message": str(exc)}), 401

    sim_ids = [s.id for s in Simulation.query.filter_by(
        company_id=company.id).all()]

    if not sim_ids:
        return jsonify({
            "success": True,
            "data": {"competitors": [], "yourCompany": None}
        }), 200

    citations = Citation.query.filter(
        Citation.simulation_id.in_(sim_ids)).all()

    # Count citations per company/domain
    company_domain = company.primary_domain or ""
    company_counts = {}
    your_count = 0

    for c in citations:
        cited = c.company_cited or c.website_domain
        if cited:
            if cited.lower() == company_domain.lower():
                your_count += 1
            else:
                company_counts[cited] = company_counts.get(cited, 0) + 1

    # Calculate total for market share
    total_citations = your_count + sum(company_counts.values())

    # Build competitor list with scores
    competitors = []
    for name, count in sorted(company_counts.items(), key=lambda x: -x[1])[:10]:
        market_share = round(count / total_citations * 100,
                             1) if total_citations else 0
        # Score is based on mention frequency (normalized)
        max_count = max(company_counts.values()) if company_counts else 1
        score = round(count / max_count * 100)
        competitors.append({
            "name": name,
            "score": score,
            "marketShare": market_share,
            "mentions": count,
            "trend": "+0%",  # TODO: calculate actual trend
        })

    # Your company stats
    your_market_share = round(
        your_count / total_citations * 100, 1) if total_citations else 0
    your_company = {
        "name": company.name,
        "mentions": your_count,
        "marketShare": your_market_share,
        "rank": 1 if not competitors or your_count >= competitors[0]["mentions"] else (
            next((i + 2 for i, c in enumerate(competitors)
                 if your_count >= c["mentions"]), len(competitors) + 1)
        ),
    }

    return jsonify({
        "success": True,
        "data": {
            "competitors": competitors,
            "yourCompany": your_company,
        }
    }), 200


# ─────────────────────────────────────────────
# Actions Page - Errors and recommendations
# ─────────────────────────────────────────────
@bp.route("/actions", methods=["GET"])
def get_actions_details():
    """Get action items: errors, issues, and recommendations."""
    try:
        user, company = require_company_session(request)
    except PermissionError as exc:
        return jsonify({"success": False, "message": str(exc)}), 401

    sim_ids = [s.id for s in Simulation.query.filter_by(
        company_id=company.id).all()]

    if not sim_ids:
        return jsonify({
            "success": True,
            "data": {"errors": [], "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0}}
        }), 200

    errors = Error.query.filter(Error.simulation_id.in_(sim_ids))\
        .order_by(desc(Error.time_created)).all()

    # Group by severity
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for e in errors:
        sev = e.severity.lower() if e.severity else "medium"
        if sev in severity_counts:
            severity_counts[sev] += 1

    # Build error list
    error_list = [
        {
            "id": e.id,
            "type": e.error_type,
            "severity": e.severity,
            "message": e.reason_for_failure,
            "suggestion": e.mitigation,
            "link": e.company_link,
            "model": e.model_name,
            "date": e.time_created.isoformat() if e.time_created else None,
        }
        for e in errors[:50]
    ]

    return jsonify({
        "success": True,
        "data": {
            "errors": error_list,
            "summary": severity_counts,
        }
    }), 200
