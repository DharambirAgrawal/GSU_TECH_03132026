from __future__ import annotations

import io
from collections import Counter
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.simulation import Citation, Error, FactCheck, PromptModelRun, Simulation


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

    error_type_counts = Counter(err.error_type for err in errors)
    top_errors = error_type_counts.most_common(3)

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
                f"Generated: {datetime.now(timezone.utc).isoformat()}"
            ),
            body,
        )
    )
    story.append(Spacer(1, 0.18 * inch))

    story.append(Paragraph("Executive Snapshot", h2))
    metrics_rows = [
        ["Metric", "Value"],
        ["Prompts processed", str(total_prompts)],
        ["Model runs", str(total_runs)],
        ["Total citations", str(total_citations)],
        ["Total errors", str(total_errors)],
        ["Dead links", str(dead_links)],
        ["Hallucination indicators", str(hallucinations)],
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
        "top_errors": [{"error_type": e, "count": c} for e, c in top_errors],
    }
    return pdf_bytes, metadata
