from __future__ import annotations

import io
from collections import Counter, defaultdict
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.simulation import (
    Citation,
    Error,
    FactCheck,
    Prompt,
    PromptModelRun,
    Simulation,
)


def _normalize_department(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized == "marketting":
        return "marketing"
    return normalized


def _strategy_for_error(error_type: str, department: str) -> str:
    strategies_engineering = {
        "dead_link": (
            "Add automated link checks in CI, enforce redirects for moved pages, and "
            "publish stable canonical URLs in sitemap and schema markup."
        ),
        "hallucination": (
            "Strengthen machine-readable product facts (JSON-LD Product/FAQ), add "
            "llms.txt, and expose exact spec endpoints for crawler access."
        ),
        "factual_error": (
            "Create a single source-of-truth content API for specs/pricing and "
            "version pages with last-updated timestamps for AI retrievers."
        ),
        "missing_brand": (
            "Increase technical discoverability for branded entities via Organization "
            "schema, consistent entity naming, and cross-page internal linking."
        ),
        "competitor_bias": (
            "Improve comparative landing pages and benchmark pages with structured "
            "tables that LLM retrieval can quote directly."
        ),
        "outdated_info": (
            "Add content freshness signals (updated_at metadata, RSS, sitemap "
            "lastmod) and remove stale duplicates from indexable routes."
        ),
    }

    strategies_marketing = {
        "dead_link": (
            "Prioritize high-intent campaign pages for link hygiene and run weekly "
            "crawl audits with ownership by channel lead."
        ),
        "hallucination": (
            "Publish concise claim-proof pages with source citations and update "
            "brand messaging docs so model-visible content stays factual."
        ),
        "factual_error": (
            "Align website copy, ad copy, and partner listings so pricing/features "
            "are consistent across all top-ranking pages."
        ),
        "missing_brand": (
            "Increase branded mention density on authoritative pages and secure "
            "third-party mentions linking back to official product pages."
        ),
        "competitor_bias": (
            "Ship clearer comparison content that directly answers 'why us' for the "
            "top competitor queries flagged in this simulation."
        ),
        "outdated_info": (
            "Create a monthly content freshness calendar for high-traffic GEO pages "
            "and refresh outdated proof points."
        ),
    }

    table = (
        strategies_engineering if department == "engineering" else strategies_marketing
    )
    return table.get(
        error_type,
        "Create a GEO remediation task with owner, deadline, and measurable KPI for the next simulation rerun.",
    )


def _pct(numerator: float | int, denominator: float | int) -> float:
    if not denominator:
        return 0.0
    return (float(numerator) / float(denominator)) * 100.0


def _signal_label(value: float, good_threshold: float, watch_threshold: float) -> str:
    if value >= good_threshold:
        return "Strong"
    if value >= watch_threshold:
        return "Watch"
    return "Needs action"


def _quality_risk_index(dead_links: int, hallucinations: int, total_runs: int) -> float:
    weighted_issues = (dead_links * 1.1) + (hallucinations * 1.6)
    if total_runs <= 0:
        return 0.0
    return min(100.0, _pct(weighted_issues, total_runs))


def _department_focus_text(department: str) -> tuple[str, str]:
    if department == "engineering":
        return (
            "Primary objective: increase retrieval reliability and factual consistency.",
            "Prioritize dead-link stability, machine-readable facts, and crawl clarity before next release.",
        )
    return (
        "Primary objective: increase recommendation share and brand trust in AI answers.",
        "Prioritize comparison messaging, proof-backed claims, and content freshness on high-intent topics.",
    )


def generate_department_report_pdf(
    simulation: Simulation,
    company_department: str,
) -> tuple[bytes, dict[str, object]]:
    department = _normalize_department(company_department)
    if department not in {"engineering", "marketing"}:
        raise ValueError(
            "company_department must be engineering or marketting/marketing"
        )

    report_summary = simulation.report_summary
    errors = Error.query.filter_by(simulation_id=simulation.id).all()
    citations = Citation.query.filter_by(simulation_id=simulation.id).all()
    fact_checks = FactCheck.query.filter_by(simulation_id=simulation.id).all()
    runs = PromptModelRun.query.filter_by(simulation_id=simulation.id).all()
    prompts = Prompt.query.filter_by(simulation_id=simulation.id).all()

    prompt_text_by_id = {prompt.id: prompt.text for prompt in prompts}

    error_type_counts = Counter(err.error_type for err in errors)
    top_errors = error_type_counts.most_common(3)

    severity_counts = Counter(err.severity for err in errors)
    critical_or_high = severity_counts.get("critical", 0) + severity_counts.get("high", 0)

    issue_counts = Counter(
        err.reason_for_failure.strip()[:160] for err in errors if err.reason_for_failure
    )
    top_issues = issue_counts.most_common(3)

    domain_counts = Counter(c.website_domain for c in citations if c.website_domain)
    top_domains = domain_counts.most_common(5)

    avg_fact = report_summary.avg_fact_score if report_summary else None
    total_prompts = (
        report_summary.total_prompts if report_summary else simulation.n_iteration
    )
    total_runs = report_summary.total_model_runs if report_summary else len(runs)
    total_errors = report_summary.total_errors if report_summary else len(errors)
    total_citations = (
        report_summary.total_citations if report_summary else len(citations)
    )
    successful_runs = sum(1 for run in runs if run.success_or_failed == "success")
    run_success_rate = _pct(successful_runs, total_runs)
    citation_density = _pct(total_citations, total_runs)

    dead_links = (
        report_summary.dead_links_count
        if report_summary
        else sum(r.dead_links_count for r in runs)
    )
    hallucinations = (
        report_summary.hallucination_count
        if report_summary
        else sum(1 for fc in fact_checks if fc.fact_score < 0.5)
    )

    quality_risk = _quality_risk_index(dead_links, hallucinations, total_runs)
    avg_fact_pct = (avg_fact or 0.0) * 100

    model_runs = defaultdict(int)
    model_errors = defaultdict(int)
    model_dead_links = defaultdict(int)
    model_fact_values = defaultdict(list)

    for run in runs:
        model = run.model_name or "unknown"
        model_runs[model] += 1
        model_dead_links[model] += int(run.dead_links_count or 0)
        if run.fact_score is not None:
            model_fact_values[model].append(float(run.fact_score))

    for err in errors:
        model = err.model_name or "unknown"
        model_errors[model] += 1

    model_rows = []
    for model_name in sorted(model_runs.keys()):
        fact_values = model_fact_values.get(model_name, [])
        avg_model_fact = (sum(fact_values) / len(fact_values)) if fact_values else None
        model_rows.append(
            {
                "model": model_name,
                "runs": model_runs[model_name],
                "errors": model_errors[model_name],
                "dead_links": model_dead_links[model_name],
                "avg_fact_pct": (avg_model_fact * 100) if avg_model_fact is not None else None,
            }
        )

    model_rows = sorted(
        model_rows,
        key=lambda row: (
            -(row["errors"] + row["dead_links"]),
            row["avg_fact_pct"] if row["avg_fact_pct"] is not None else 999,
        ),
    )

    error_counts_by_prompt = Counter(err.prompt_id for err in errors)
    fact_scores_by_prompt = defaultdict(list)
    for check in fact_checks:
        fact_scores_by_prompt[check.prompt_id].append(float(check.fact_score))

    prompt_hotspots = []
    for prompt_id, text in prompt_text_by_id.items():
        prompt_errors = error_counts_by_prompt.get(prompt_id, 0)
        prompt_fact_values = fact_scores_by_prompt.get(prompt_id, [])
        prompt_avg_fact = (
            sum(prompt_fact_values) / len(prompt_fact_values) if prompt_fact_values else None
        )
        if prompt_errors == 0 and prompt_avg_fact is None:
            continue

        risk_score = (prompt_errors * 2.0) + (
            (1.0 - prompt_avg_fact) * 3.0 if prompt_avg_fact is not None else 1.2
        )
        prompt_hotspots.append(
            {
                "prompt_id": prompt_id,
                "text": text,
                "errors": prompt_errors,
                "avg_fact_pct": (prompt_avg_fact * 100) if prompt_avg_fact is not None else None,
                "risk_score": risk_score,
            }
        )

    prompt_hotspots = sorted(prompt_hotspots, key=lambda row: row["risk_score"], reverse=True)[:5]

    focus_primary, focus_secondary = _department_focus_text(department)
    top_error_type = top_errors[0][0] if top_errors else None
    top_error_count = top_errors[0][1] if top_errors else 0

    if department == "engineering":
        priority_actions = [
            f"Fix {critical_or_high} critical/high-severity issues in this cycle (start with {top_error_type or 'highest-volume error'}).",
            "Repair dead links and canonical routes on the top cited domains before the next simulation.",
            "Add/verify schema + llms.txt coverage on high-risk prompts highlighted below.",
            "Re-run simulation after fixes and target lower quality-risk index than this report.",
        ]
    else:
        priority_actions = [
            f"Address top narrative failure ({top_error_type or 'content inconsistency'}) impacting {top_error_count} occurrences.",
            "Refresh comparison pages and proof-backed claim pages for high-risk prompts.",
            "Prioritize top citation domains for partnership/content amplification.",
            "Re-run simulation and aim for higher citation density and fact score lift.",
        ]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"GEO Action Report - {simulation.id}",
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]

    story = []
    story.append(Paragraph(f"GEO Action Report - {department.title()}", title_style))
    story.append(
        Paragraph(
            (
                f"Simulation ID: {simulation.id}<br/>"
                f"Company ID: {simulation.company_id}<br/>"
                f"Product Focus: {simulation.product_specification}<br/>"
                f"Run Status: {simulation.status}<br/>"
                f"Generated: {datetime.now(timezone.utc).isoformat()}"
            ),
            body,
        )
    )
    if simulation.additional_detail:
        story.append(Paragraph(f"Additional context: {simulation.additional_detail[:280]}", body))
    story.append(Paragraph(focus_primary, body))
    story.append(Paragraph(focus_secondary, body))
    story.append(Spacer(1, 0.18 * inch))

    story.append(Paragraph("Executive Snapshot", h2))
    metrics_rows = [
        ["Metric", "Value"],
        ["Prompts processed", str(total_prompts)],
        ["Model runs", str(total_runs)],
        ["Total citations", str(total_citations)],
        ["Total errors", str(total_errors)],
        ["Critical + High issues", str(critical_or_high)],
        ["Dead links", str(dead_links)],
        ["Hallucination indicators", str(hallucinations)],
        ["Run success rate", f"{run_success_rate:.1f}%"],
        ["Citation density (citations / run)", f"{citation_density:.1f}%"],
        ["Quality risk index", f"{quality_risk:.1f}/100"],
        ["Average fact score", f"{avg_fact:.2f}" if avg_fact is not None else "N/A"],
    ]
    table = Table(metrics_rows, colWidths=[2.8 * inch, 3.8 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#F9FAFB")],
                ),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Department Scorecard", h2))
    scorecard_rows = [
        ["Signal", "Current", "Status"],
        [
            "Fact quality",
            f"{avg_fact_pct:.1f}%",
            _signal_label(avg_fact_pct, good_threshold=78.0, watch_threshold=62.0),
        ],
        [
            "Reliability risk",
            f"{quality_risk:.1f}/100",
            "Strong" if quality_risk < 25 else "Watch" if quality_risk < 45 else "Needs action",
        ],
        [
            "Execution stability",
            f"{run_success_rate:.1f}%",
            _signal_label(run_success_rate, good_threshold=92.0, watch_threshold=80.0),
        ],
    ]
    scorecard = Table(scorecard_rows, colWidths=[2.4 * inch, 1.6 * inch, 2.6 * inch])
    scorecard.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ]
        )
    )
    story.append(scorecard)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Top Priority Actions (Next 7 Days)", h2))
    for action in priority_actions:
        story.append(Paragraph(f"- {action}", body))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Top 3 Actionable Error Types", h2))
    if not top_errors:
        story.append(Paragraph("No errors found in this simulation.", body))
    else:
        for error_type, count in top_errors:
            strategy = _strategy_for_error(error_type, department)
            story.append(Paragraph(f"<b>{error_type}</b> - occurrences: {count}", body))
            story.append(Paragraph(f"Recommended GEO mitigation: {strategy}", body))
            story.append(Spacer(1, 0.08 * inch))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Top 3 Issues (Failure Reasons)", h2))
    if not top_issues:
        story.append(Paragraph("No issue strings were recorded.", body))
    else:
        for reason, count in top_issues:
            story.append(Paragraph(f"- {reason} (count: {count})", body))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Top Citation Domains", h2))
    if not top_domains:
        story.append(Paragraph("No citations available.", body))
    else:
        for domain, count in top_domains:
            story.append(Paragraph(f"- {domain} (citations: {count})", body))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Model Performance Signals", h2))
    if not model_rows:
        story.append(Paragraph("No model-run data available.", body))
    else:
        model_table_rows = [["Model", "Runs", "Errors", "Dead Links", "Avg Fact %"]]
        for row in model_rows[:6]:
            model_table_rows.append(
                [
                    row["model"],
                    str(row["runs"]),
                    str(row["errors"]),
                    str(row["dead_links"]),
                    f"{row['avg_fact_pct']:.1f}%" if row["avg_fact_pct"] is not None else "N/A",
                ]
            )
        model_table = Table(
            model_table_rows,
            colWidths=[1.6 * inch, 0.8 * inch, 0.8 * inch, 1.0 * inch, 1.2 * inch],
        )
        model_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                ]
            )
        )
        story.append(model_table)

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Prompt Hotspots (Most Likely to Need Updates)", h2))
    if not prompt_hotspots:
        story.append(Paragraph("No prompt-level hotspots were detected.", body))
    else:
        for index, hotspot in enumerate(prompt_hotspots, start=1):
            fact_text = (
                f"{hotspot['avg_fact_pct']:.1f}%"
                if hotspot["avg_fact_pct"] is not None
                else "N/A"
            )
            prompt_preview = (hotspot["text"] or "").strip().replace("\n", " ")[:180]
            story.append(
                Paragraph(
                    f"{index}. Prompt: {prompt_preview}<br/>"
                    f"Errors: {hotspot['errors']} | Avg fact: {fact_text}",
                    body,
                )
            )
            story.append(Spacer(1, 0.05 * inch))

    story.append(Spacer(1, 0.15 * inch))
    section_title = (
        "Engineering GEO Playbook"
        if department == "engineering"
        else "Marketing GEO Playbook"
    )
    story.append(Paragraph(section_title, h2))
    if department == "engineering":
        actions = [
            "Implement schema coverage checks (Organization, Product, FAQ) in CI before content deployment.",
            "Expose clean canonical URLs and eliminate redirect chains on high-intent pages.",
            "Publish machine-readable product facts and pricing change logs for crawler trust.",
            "Create llms.txt plus crawlable knowledge pages specifically for AI retrieval.",
            "Run nightly dead-link checks and auto-open tickets for broken references.",
        ]
    else:
        actions = [
            "Refresh brand comparison pages for the top competitor prompts from this simulation.",
            "Publish evidence-backed claim pages with third-party citations and clear update dates.",
            "Create an editorial GEO calendar to improve freshness for high-intent product topics.",
            "Align campaign messaging with on-site copy to reduce contradictory model signals.",
            "Increase mentions in authoritative external publications and link back to canonical pages.",
        ]
    for item in actions:
        story.append(Paragraph(f"- {item}", body))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    metadata = {
        "filename": f"geo_report_{department}_{simulation.id}.pdf",
        "department": department,
        "simulation_id": simulation.id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_errors": total_errors,
        "run_success_rate": round(run_success_rate, 2),
        "citation_density": round(citation_density, 2),
        "quality_risk_index": round(quality_risk, 2),
        "top_errors": [{"error_type": e, "count": c} for e, c in top_errors],
    }
    return pdf_bytes, metadata
