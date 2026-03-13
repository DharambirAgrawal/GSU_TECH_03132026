from __future__ import annotations

import logging
from urllib.parse import urlparse
import logging
from urllib.parse import urlparse

from app.extensions import db
from app.models.simulation import Citation, Error, FactCheck, Prompt, PromptModelRun, Simulation
from app.services.emailing import send_email
from app.services.fact_check import fact_check as nlp_fact_check
from app.services.metrices_generator import analyze_llm_response, generate_report_summary
from app.utils.link_parser import parse_links_with_context
from app.utils.llm_clients import query_all_llms
from app.utils.query_generator import COMPANY_PROFILES

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Path 1 uses Gemini 2.5 Pro for deep brand-visibility analysis (expensive).
# Only run it on the two models whose structured outputs are richest for that.
# ──────────────────────────────────────────────────────────────────────────────
_PATH1_MODELS = frozenset({"chatgpt", "gemini"})

# Guard against checking hundreds of links per response (each link = HTTP fetch).
_MAX_PATH2_URLS = 20


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def _normalize_domain(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = parsed.hostname or text
    return host.removeprefix("www.")


def _extract_bare_domain(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
        return host.removeprefix("www.")
    except Exception:
        return ""


def _is_noise_url(url: str) -> bool:
    """True for tracking pixels, Google/Bing redirect shims, empty slugs, etc."""
    lower = url.lower()
    noise_patterns = (
        "google.com/url",
        "bing.com/ck",
        "/search?",
        "translate.google",
        "webcache.googleusercontent",
        "javascript:",
        "mailto:",
    )
    return any(p in lower for p in noise_patterns) or len(url) < 12


def _create_basic_run(
    simulation_id: str,
    prompt_id: str,
    model_name: str,
    source_count: int,
) -> str:
    """
    Create a minimal PromptModelRun for models that skip Path 1.
    Returns the new run's id after flushing (before commit).
    """
    run = PromptModelRun(
        simulation_id=simulation_id,
        prompt_id=prompt_id,
        model_name=model_name,
        success_or_failed="success",
        citations_found_count=source_count,
        dead_links_count=0,
    )
    db.session.add(run)
    db.session.flush()
    return run.id


def _update_run_dead_count(run_id: str, dead_delta: int) -> None:
    """Increment the dead_links_count on an existing PromptModelRun."""
    run = PromptModelRun.query.get(run_id)
    if run is not None and dead_delta > 0:
        run.dead_links_count = (run.dead_links_count or 0) + dead_delta
        db.session.flush()


# ─────────────────────────────────────────────────────────────────────────────
# PATH 2: NLP LINK FACT-CHECKING
# ─────────────────────────────────────────────────────────────────────────────


def _run_path2_nlp_fact_checks(
    simulation_id: str,
    prompt_id: str,
    run_id: str,
    model_name: str,
    content: str,
    sources: list[dict],
    create_citations: bool,
) -> dict[str, int]:
    """
    For every URL found in the LLM response:

    1. parse_links_with_context()  — extracts inline links & their label context
    2. Merge structured `sources` list so nothing is missed
    3. For each unique, non-noise URL (up to _MAX_PATH2_URLS):
         • Try nlp_fact_check(url, content)  → TF-IDF similarity score
         • Write FactCheck row
         • Write Citation row (if create_citations=True)
         • Write Error row if score is low (hallucination indicator)
         • Write Error row if URL fetch fails (dead link)

    Returns stats dict.
    """
    # ── collect & deduplicate links ──────────────────────────────────────────
    parsed = parse_links_with_context(content)  # [(url, label), ...]

    seen: set[str] = set()
    all_links: list[tuple[str, str]] = []

    for url, ctx in parsed:
        if url not in seen and not _is_noise_url(url):
            seen.add(url)
            all_links.append((url, ctx))

    # merge structured sources that weren't in the inline text
    for src in sources:
        url = src.get("url", "")
        if url and url not in seen and not _is_noise_url(url):
            seen.add(url)
            all_links.append((url, src.get("title", "source")))

    all_links = all_links[:_MAX_PATH2_URLS]

    stats = {"total": len(all_links), "passed": 0, "low_score": 0, "dead": 0, "errors": 0}

    for url, ctx in all_links:
        domain = _extract_bare_domain(url)

        try:
            result = nlp_fact_check(url, content)

            # ── always write a FactCheck row ────────────────────────────────
            db.session.add(FactCheck(
                simulation_id=simulation_id,
                prompt_id=prompt_id,
                run_id=run_id,
                company_link=url,
                ai_text_about=content[:2000],
                fact_score=result.fact_score,
                reason_for_score=result.reason_for_score,
                mitigation=result.mitigation,
                model_name=model_name,
            ))

            # ── Citation (only for models that skipped Path 1) ───────────────
            if create_citations:
                db.session.add(Citation(
                    simulation_id=simulation_id,
                    prompt_id=prompt_id,
                    run_id=run_id,
                    company_cited=ctx[:255],
                    website_domain=domain or "unknown",
                    cited_url=url,
                    model_name=model_name,
                ))

            # ── hallucination / low-support Error ────────────────────────────
            if result.fact_score < 0.35:
                stats["low_score"] += 1
                severity = "critical" if result.fact_score < 0.15 else "high" if result.fact_score < 0.25 else "medium"
                db.session.add(Error(
                    simulation_id=simulation_id,
                    prompt_id=prompt_id,
                    run_id=run_id,
                    company_link=url,
                    error_type="hallucination" if result.fact_score < 0.20 else "factual_error",
                    severity=severity,
                    reason_for_failure=(
                        f"NLP fact-check score {result.fact_score:.2f} — "
                        + result.reason_for_score[:500]
                    ),
                    mitigation=result.mitigation[:500],
                    model_name=model_name,
                ))
            else:
                stats["passed"] += 1

        except RuntimeError:
            # URL could not be fetched → dead link
            stats["dead"] += 1
            logger.debug("[path2] dead link: %s (%s)", url, model_name)

            if create_citations:
                db.session.add(Citation(
                    simulation_id=simulation_id,
                    prompt_id=prompt_id,
                    run_id=run_id,
                    company_cited=ctx[:255],
                    website_domain=domain or "unknown",
                    cited_url=url,
                    model_name=model_name,
                ))

            db.session.add(Error(
                simulation_id=simulation_id,
                prompt_id=prompt_id,
                run_id=run_id,
                company_link=url,
                error_type="dead_link",
                severity="high",
                reason_for_failure=f"URL unreachable during NLP fact-check: {url}",
                mitigation=(
                    "Verify the page is publicly indexed. "
                    "Submit to sitemaps and check for login walls or geo-blocks."
                ),
                model_name=model_name,
            ))

        except Exception as exc:
            stats["errors"] += 1
            logger.warning("[path2] nlp_fact_check unexpected error | url=%s model=%s: %s", url, model_name, exc)

    db.session.commit()
    _update_run_dead_count(run_id, stats["dead"])
    db.session.commit()

    logger.info(
        "[path2] %s | sim=%s | urls=%d passed=%d low_score=%d dead=%d errors=%d",
        model_name, simulation_id[:8],
        stats["total"], stats["passed"], stats["low_score"], stats["dead"], stats["errors"],
    )
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AUTOMATION
# ─────────────────────────────────────────────────────────────────────────────


def agentic_geo_automation(
    simulation_id: str,
    recipient_email: str | None,
    frontend_base_url: str,
) -> dict[str, object]:
    """
    Full two-path simulation pipeline.

    Path 1  (chatgpt + gemini only)
    ────────────────────────────────
    analyze_llm_response() → Gemini 2.5 Pro deep brand-visibility analysis.
    Writes: PromptModelRun, Citation, Error, FactCheck (holistic brand score).

    Path 2  (all four models)
    ──────────────────────────
    link_parser → nlp_fact_check() per URL → per-URL NLP fact score.
    Writes: additional FactCheck rows, Error rows (low score / dead links),
            Citation rows (for claude & perplexity which skip Path 1).

    For claude + perplexity a minimal PromptModelRun is created before Path 2
    so all child records have a valid run_id FK.
    """
    simulation = Simulation.query.get(simulation_id)
    if simulation is None:
        return {
            "simulation_id": simulation_id,
            "processed_prompts": 0,
            "model_runs_created": 0,
            "email_sent": False,
            "delay_seconds": 0,
        }

    company = simulation.company
    company_name = company.name if company else "Unknown"
    company_domain = _normalize_domain(simulation.url)
    if not company_domain:
        company_domain = _normalize_domain(company.primary_domain if company else "")

    profile = COMPANY_PROFILES.get(company_name.strip().lower(), {})
    competitors: list[str] = list(profile.get("competitors", []))

    about_company = simulation.about_company or (company.about_company if company else None)
    product_specification = simulation.product_specification

    prompts = (
        Prompt.query.filter_by(simulation_id=simulation_id)
        .order_by(Prompt.prompt_order.asc(), Prompt.time_created.asc())
        .all()
    )

    processed_prompts = 0
    model_runs_created = 0

    logger.info(
        "[automation] Starting simulation %s | prompts=%d | company=%s",
        simulation_id, len(prompts), company_name,
    )

    for prompt in prompts:
        processed_prompts += 1
        responses = query_all_llms(prompt.text, search=True)

        for model_name, response in responses.items():
            content = (response.content or "").strip()

            # ── complete API failure → record and skip both paths ─────────────
            if content.startswith("[ERROR]"):
                db.session.add(PromptModelRun(
                    simulation_id=simulation_id,
                    prompt_id=prompt.id,
                    model_name=model_name,
                    success_or_failed="failed",
                    failure_reason=content,
                    mitigation="Retry after rate limits clear or API credentials are refreshed.",
                    citations_found_count=0,
                    dead_links_count=0,
                ))
                db.session.commit()
                model_runs_created += 1
                logger.warning("[automation] %s returned error, skipping | sim=%s", model_name, simulation_id[:8])
                continue

            if not content:
                logger.warning("[automation] %s returned empty content, skipping | sim=%s", model_name, simulation_id[:8])
                continue

            run_id: str | None = None

            # ═════════════════════════════════════════════════════════════════
            # PATH 1  —  Gemini brand-visibility analysis  (chatgpt + gemini)
            # ═════════════════════════════════════════════════════════════════
            if model_name in _PATH1_MODELS:
                try:
                    result = analyze_llm_response(
                        simulation_id=simulation_id,
                        prompt_id=prompt.id,
                        prompt_text=prompt.text,
                        llm_response_text=content,
                        model_name=model_name,
                        sources=response.sources,
                        company_name=company_name,
                        company_domain=company_domain,
                        competitors=competitors,
                        product_specification=product_specification,
                        about_company=about_company,
                        check_url_liveness=True,
                    )
                    run_id = result.get("run_id")
                    model_runs_created += 1
                    logger.info(
                        "[path1] %s | brand_mentioned=%s rank=%s fact=%s | sim=%s",
                        model_name,
                        result.get("brand_mentioned"),
                        result.get("brand_rank"),
                        result.get("fact_score"),
                        simulation_id[:8],
                    )
                except Exception as exc:
                    logger.exception(
                        "[path1] analyze_llm_response failed | sim=%s prompt=%s model=%s",
                        simulation_id, prompt.id, model_name,
                    )
                    db.session.rollback()
                    # create a failed run so path 2 still has something to attach to
                    try:
                        run = PromptModelRun(
                            simulation_id=simulation_id,
                            prompt_id=prompt.id,
                            model_name=model_name,
                            success_or_failed="failed",
                            failure_reason=str(exc)[:2000],
                            mitigation="Inspect server logs and rerun simulation.",
                            citations_found_count=len(response.sources),
                            dead_links_count=0,
                        )
                        db.session.add(run)
                        db.session.flush()
                        run_id = run.id
                        db.session.commit()
                        model_runs_created += 1
                    except Exception:
                        db.session.rollback()
                        logger.exception("[automation] could not persist failed run for %s", model_name)

            # ═════════════════════════════════════════════════════════════════
            # For claude / perplexity: create basic run before Path 2
            # ═════════════════════════════════════════════════════════════════
            else:
                try:
                    run_id = _create_basic_run(
                        simulation_id=simulation_id,
                        prompt_id=prompt.id,
                        model_name=model_name,
                        source_count=len(response.sources),
                    )
                    db.session.commit()
                    model_runs_created += 1
                except Exception:
                    db.session.rollback()
                    logger.exception("[automation] could not create basic run for %s", model_name)
                    run_id = None

            # ═════════════════════════════════════════════════════════════════
            # PATH 2  —  NLP link fact-checking  (ALL models)
            # ═════════════════════════════════════════════════════════════════
            if run_id:
                try:
                    _run_path2_nlp_fact_checks(
                        simulation_id=simulation_id,
                        prompt_id=prompt.id,
                        run_id=run_id,
                        model_name=model_name,
                        content=content,
                        sources=response.sources,
                        # Path 1 models already have Citations written; skip duplicates.
                        create_citations=(model_name not in _PATH1_MODELS),
                    )
                except Exception:
                    db.session.rollback()
                    logger.exception(
                        "[path2] unexpected failure | sim=%s prompt=%s model=%s",
                        simulation_id, prompt.id, model_name,
                    )

    # ── Aggregate everything into the ReportSummary row ──────────────────────
    generate_report_summary(simulation_id)

    # ── Completion email ──────────────────────────────────────────────────────
    email_sent = False
    if recipient_email:
        login_url = f"{frontend_base_url.rstrip('/')}/login"
        message = (
            "Your simulation has completed.\n\n"
            f"Simulation ID: {simulation_id}\n"
            f"Prompts processed: {processed_prompts}\n"
            f"Model runs analyzed: {model_runs_created}\n"
            "Please login to view your results.\n"
            f"Login: {login_url}"
        )
        try:
            send_email(
                recipient=recipient_email,
                subject="Simulation completed",
                message=message,
            )
            email_sent = True
        except Exception:
            email_sent = False

    logger.info(
        "[automation] Done | sim=%s | prompts=%d runs=%d email_sent=%s",
        simulation_id[:8], processed_prompts, model_runs_created, email_sent,
    )

    return {
        "simulation_id": simulation_id,
        "processed_prompts": processed_prompts,
        "model_runs_created": model_runs_created,
        "delay_seconds": 0,
        "processed_prompts": processed_prompts,
        "model_runs_created": model_runs_created,
        "delay_seconds": 0,
        "email_sent": email_sent,
    }
