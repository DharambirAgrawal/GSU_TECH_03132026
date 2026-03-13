"""
Metrics to get from what the database give

 Brand mention per query - against competitors - every 100 queries.
    - Divide across LLMS - Gpt x%, Gemini y%

- Answers citing company website per total mention
    E.g. Dell. How many were mentioned by chat were from the company website.
    - Which other domains do the AI get info about the product

- Ranking among competitors  - DONE
    - mentions and for links per query (...)
    - Top Recommendation Rate
    - Ranking

- Factual score - DONE
    - Links Based on AI output about A Link/product vs actual content. if it's related, if it contains the valid info

- Errors - DONE
    Link route | error code/type

Output these metrics based on models in the db. Get the insights from thoughs models
"""

from __future__ import annotations

import json
import logging
import os
import time
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.extensions import db
from app.models.simulation import Citation, Error, FactCheck, PromptModelRun

load_dotenv()
logger = logging.getLogger(__name__)

_PREFERRED_MODEL = os.environ.get("GEMINI_ANALYTICS_MODEL", "gemini-2.5-pro-preview-05-06")
_FALLBACK_MODEL = "gemini-2.5-flash"
_URL_CHECK_TIMEOUT = 8


def _extract_domain(url: str) -> str:
    """Return bare hostname, e.g. 'ebay.com' from 'https://www.ebay.com/...'"""
    try:
        host = urlparse(url).hostname or ""
        return host.removeprefix("www.")
    except Exception:
        return ""


def _check_url_alive(url: str) -> bool:
    """Return True if the URL responds with a non-5xx status within timeout."""
    try:
        with httpx.Client(timeout=_URL_CHECK_TIMEOUT, follow_redirects=True) as client:
            resp = client.head(url)
            return resp.status_code < 500
    except Exception:
        return False


def _call_gemini_analysis(prompt: str, retries: int = 5) -> dict:
    """
    Call Gemini with `prompt`, returning parsed JSON dict.
    Tries _PREFERRED_MODEL first, falls back to _FALLBACK_MODEL.
    Exponential back-off on 429 / quota errors.
    """
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    for model in (_PREFERRED_MODEL, _FALLBACK_MODEL):
        wait = 4
        for attempt in range(retries):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            "You are a precise JSON-only analytics engine. "
                            "Output ONLY valid JSON — no markdown, no code fences, no commentary."
                        ),
                        temperature=0.1,
                    ),
                )
                raw = ""
                try:
                    raw = response.text or ""
                except Exception:
                    try:
                        raw = response.candidates[0].content.parts[0].text or ""
                    except Exception:
                        raw = ""

                raw = raw.strip()
                if raw.startswith("```"):
                    parts = raw.split("```")
                    if len(parts) >= 3:
                        raw = parts[1]
                    raw = raw.removeprefix("json").strip()
                    if raw.endswith("```"):
                        raw = raw[:-3].strip()

                return json.loads(raw)

            except Exception as exc:
                err_str = str(exc).lower()
                is_quota = any(
                    k in err_str for k in ("429", "quota", "rate", "resource_exhausted")
                )
                if is_quota and attempt < retries - 1:
                    logger.warning(
                        f"Gemini {model} rate limited (attempt {attempt + 1}). Retrying in {wait}s..."
                    )
                    time.sleep(wait)
                    wait = min(wait * 2, 120)
                else:
                    logger.error(f"Gemini {model} analysis error: {exc}")
                    break

    logger.error("All Gemini analysis attempts failed; returning empty metrics.")
    return {}


def _build_analysis_prompt(
    prompt_text: str,
    llm_response_text: str,
    model_name: str,
    company_name: str,
    company_domain: str,
    competitors: list[str],
    product_specification: str,
    about_company: str | None,
    sources: list[dict],
) -> str:
    sources_block = ""
    if sources:
        sources_block = "\n\nSOURCES CITED BY THE LLM:\n"
        for src in sources:
            sources_block += (
                f"  [{src.get('rank', '?')}] {src.get('title', 'Untitled')}"
                f" — {src.get('url', 'N/A')}\n"
            )
            if src.get("snippet"):
                sources_block += f"      Snippet: {src['snippet'][:150]}\n"

    about_block = (
        f"\nCOMPANY BACKGROUND (ground truth for fact-checking):\n{about_company}\n"
        if about_company
        else ""
    )
    competitor_list = ", ".join(competitors) if competitors else "Unknown"

    schema = """{
  "brand_mentioned": <bool>,
  "brand_mention_count": <int>,
  "brand_rank": <int or null>,
  "brand_sentiment": "<positive|negative|neutral|not_mentioned>",
  "brand_is_top_recommendation": <bool>,
  "brand_mention_context": "<1-2 sentence description>",
  "competitors_mentioned": [
    {"name": "<name>", "mention_count": <int>, "rank": <int or null>, "sentiment": "<positive|negative|neutral>"}
  ],
  "citations": [
    {
      "company_cited": "<entity name>",
      "website_domain": "<bare domain>",
      "cited_url": "<full URL>",
      "is_company_domain": <bool>,
      "is_competitor_domain": <bool>,
      "relevance": "<high|medium|low>"
    }
  ],
  "fact_assessment": {
    "fact_score": <float 0.0-1.0>,
    "reason": "<explanation>",
    "potential_hallucinations": ["<claim>"],
    "mitigation": "<recommendation>"
  },
  "errors": [
    {
      "error_type": "<dead_link|hallucination|factual_error|missing_brand|competitor_bias|outdated_info>",
      "severity": "<critical|high|medium|low>",
      "company_link": "<URL or null>",
      "reason_for_failure": "<description>",
      "mitigation": "<recommendation>"
    }
  ],
  "overall_visibility_score": <float 0.0-1.0>,
  "summary": "<executive summary paragraph>"
}"""

    return (
        f"You are an expert AI brand-visibility and accuracy analytics engine.\n\n"
        f"============================\nMONITORING CONTEXT\n============================\n"
        f"Company Being Monitored : {company_name}\n"
        f"Company Primary Domain  : {company_domain}\n"
        f"Product / Topic         : {product_specification}\n"
        f"LLM That Generated Response: {model_name}\n"
        f"Known Competitors       : {competitor_list}\n"
        f"{about_block}\n"
        f"============================\nCONSUMER QUERY:\n{prompt_text}\n\n"
        f"============================\nLLM RESPONSE TO ANALYZE:\n{llm_response_text}\n"
        f"{sources_block}\n"
        f"============================\n\n"
        f"Perform a deep analysis. Respond with a SINGLE valid JSON object using this schema:\n"
        f"{schema}\n\n"
        f"RULES:\n"
        f"- brand_rank=1 means first/primary recommendation; null if not mentioned at all.\n"
        f"- fact_score=1.0 means every claim about {company_name} is verifiably accurate.\n"
        f"- overall_visibility_score: weighted holistic score (rank + sentiment + citation quality + fact accuracy).\n"
        f"- Extract EVERY URL from both response text AND the sources list.\n"
        f"- ONLY flag errors that genuinely exist — do NOT fabricate.\n"
        f"- Output ONLY the JSON object. Nothing else."
    )


def analyze_llm_response(
    simulation_id: str,
    prompt_id: str,
    prompt_text: str,
    llm_response_text: str,
    model_name: str,
    sources: list[dict],
    company_name: str,
    company_domain: str,
    competitors: list[str],
    product_specification: str,
    about_company: str | None = None,
    check_url_liveness: bool = True,
) -> dict:
    """
    Analyze one LLM response and persist all metrics (PromptModelRun, Citation,
    Error, FactCheck) to the DB in a single transaction.

    Returns a summary dict with key metrics.
    """
    logger.info(f"[metrics] Analyzing {model_name} response for simulation {simulation_id}")

    analysis_prompt = _build_analysis_prompt(
        prompt_text=prompt_text,
        llm_response_text=llm_response_text,
        model_name=model_name,
        company_name=company_name,
        company_domain=company_domain,
        competitors=competitors,
        product_specification=product_specification,
        about_company=about_company,
        sources=sources,
    )

    analysis = _call_gemini_analysis(analysis_prompt)

    if not analysis:
        run = PromptModelRun(
            simulation_id=simulation_id,
            prompt_id=prompt_id,
            model_name=model_name,
            success_or_failed="failed",
            failure_reason="Gemini analysis returned no data.",
            mitigation="Retry analysis or check Gemini API quota.",
            citations_found_count=len(sources),
            dead_links_count=0,
        )
        db.session.add(run)
        db.session.commit()
        return {"run_id": run.id, "error": "analysis_failed"}

    # Merge source URLs not caught by Gemini
    cited_urls: list[dict] = list(analysis.get("citations", []))
    gemini_urls = {c.get("cited_url", "") for c in cited_urls}
    for src in sources:
        url = src.get("url", "")
        if url and url not in gemini_urls:
            cited_urls.append({
                "company_cited": src.get("title", "Unknown"),
                "website_domain": _extract_domain(url),
                "cited_url": url,
                "is_company_domain": company_domain.lower() in _extract_domain(url),
                "is_competitor_domain": any(c.lower() in url.lower() for c in competitors),
                "relevance": "medium",
            })

    # URL liveness checks
    dead_links_count = 0
    if check_url_liveness:
        for citation in cited_urls:
            url = citation.get("cited_url", "")
            if url and url != "N/A" and url.startswith("http"):
                alive = _check_url_alive(url)
                citation["is_dead"] = not alive
                if not alive:
                    dead_links_count += 1
            else:
                citation["is_dead"] = False

    fact_data = analysis.get("fact_assessment", {})
    fact_score = fact_data.get("fact_score")
    fact_reason = fact_data.get("reason", "")

    run = PromptModelRun(
        simulation_id=simulation_id,
        prompt_id=prompt_id,
        model_name=model_name,
        success_or_failed="success",
        citations_found_count=len(cited_urls),
        dead_links_count=dead_links_count,
        fact_score=fact_score,
        fact_score_reason=fact_reason,
    )
    db.session.add(run)
    db.session.flush()  # get run.id before children

    # Persist Citations (+ dead-link Error records)
    for cit in cited_urls:
        url = cit.get("cited_url", "")
        if not url or url == "N/A":
            continue
        db.session.add(Citation(
            simulation_id=simulation_id,
            prompt_id=prompt_id,
            run_id=run.id,
            company_cited=cit.get("company_cited", "Unknown"),
            website_domain=cit.get("website_domain") or _extract_domain(url),
            cited_url=url,
            model_name=model_name,
        ))
        if cit.get("is_dead"):
            db.session.add(Error(
                simulation_id=simulation_id,
                prompt_id=prompt_id,
                run_id=run.id,
                company_link=url,
                error_type="dead_link",
                severity="high",
                reason_for_failure=f"URL returned no successful response: {url}",
                mitigation=(
                    "Ensure the cited page is live and indexed. "
                    "Submit sitemaps and check for redirect chains."
                ),
                model_name=model_name,
            ))

    # Persist Errors from Gemini analysis (skip dead_link — handled above)
    for err in analysis.get("errors", []):
        if err.get("error_type") == "dead_link":
            continue
        db.session.add(Error(
            simulation_id=simulation_id,
            prompt_id=prompt_id,
            run_id=run.id,
            company_link=err.get("company_link"),
            error_type=err.get("error_type", "unknown"),
            severity=err.get("severity", "medium"),
            reason_for_failure=err.get("reason_for_failure", ""),
            mitigation=err.get("mitigation", ""),
            model_name=model_name,
        ))

    # Persist FactCheck
    if fact_score is not None:
        db.session.add(FactCheck(
            simulation_id=simulation_id,
            prompt_id=prompt_id,
            run_id=run.id,
            company_link=f"https://{company_domain}",
            ai_text_about=llm_response_text[:2000],
            fact_score=fact_score,
            reason_for_score=fact_reason,
            mitigation=fact_data.get("mitigation", ""),
            model_name=model_name,
        ))

    db.session.commit()
    logger.info(
        f"[metrics] done {model_name} | sim={simulation_id[:8]} | "
        f"brand_mentioned={analysis.get('brand_mentioned')} | "
        f"rank={analysis.get('brand_rank')} | fact={fact_score} | "
        f"citations={len(cited_urls)} | dead={dead_links_count}"
    )

    return {
        "run_id": run.id,
        "brand_mentioned": analysis.get("brand_mentioned", False),
        "brand_rank": analysis.get("brand_rank"),
        "brand_sentiment": analysis.get("brand_sentiment", "not_mentioned"),
        "brand_is_top_recommendation": analysis.get("brand_is_top_recommendation", False),
        "competitors_mentioned": analysis.get("competitors_mentioned", []),
        "fact_score": fact_score,
        "citations_found": len(cited_urls),
        "dead_links": dead_links_count,
        "errors_found": len(analysis.get("errors", [])),
        "overall_visibility_score": analysis.get("overall_visibility_score"),
        "summary": analysis.get("summary", ""),
        "full_analysis": analysis,
    }


def generate_report_summary(simulation_id: str) -> None:
    """
    Aggregate all metrics for a simulation and write (or update) the
    ReportSummary row. Call this after all prompts have been processed.
    """
    from collections import Counter

    from app.models.simulation import (
        Citation,
        Error,
        FactCheck,
        Prompt,
        PromptModelRun,
        ReportSummary,
        Simulation,
    )

    sim = Simulation.query.get(simulation_id)
    if sim is None:
        logger.error(f"generate_report_summary: simulation {simulation_id} not found")
        return

    runs = PromptModelRun.query.filter_by(simulation_id=simulation_id).all()
    citations = Citation.query.filter_by(simulation_id=simulation_id).all()
    errors = Error.query.filter_by(simulation_id=simulation_id).all()
    fact_checks = FactCheck.query.filter_by(simulation_id=simulation_id).all()

    total_prompts = Prompt.query.filter_by(simulation_id=simulation_id).count()
    dead_links = sum(r.dead_links_count for r in runs)
    hallucination_count = sum(
        1 for fc in fact_checks if fc.fact_score is not None and fc.fact_score < 0.5
    )
    scored = [fc.fact_score for fc in fact_checks if fc.fact_score is not None]
    avg_fact_score = (sum(scored) / len(scored)) if scored else None

    failure_counter: Counter = Counter(
        e.reason_for_failure[:120] for e in errors if e.reason_for_failure
    )
    mit_counter: Counter = Counter(
        e.mitigation[:120] for e in errors if e.mitigation
    )

    if avg_fact_score is not None:
        summary_text = (
            f"Processed {len(runs)} model runs across {total_prompts} prompts. "
            f"Avg fact score: {avg_fact_score:.2f}. "
            f"Dead links detected: {dead_links}. "
            f"Potential hallucinations: {hallucination_count}."
        )
    else:
        summary_text = (
            f"Processed {len(runs)} model runs across {total_prompts} prompts."
        )

    existing = ReportSummary.query.filter_by(simulation_id=simulation_id).first()
    report = existing or ReportSummary(simulation_id=simulation_id)
    if not existing:
        db.session.add(report)

    report.total_prompts = total_prompts
    report.total_model_runs = len(runs)
    report.total_citations = len(citations)
    report.total_errors = len(errors)
    report.dead_links_count = dead_links
    report.hallucination_count = hallucination_count
    report.avg_fact_score = avg_fact_score
    report.top_failure_reasons = [
        {"reason": r, "count": c} for r, c in failure_counter.most_common(5)
    ]
    report.top_mitigations = (
        [{"mitigation": m, "count": c} for m, c in mit_counter.most_common(5)]
    )
    report.competitor_comparison_summary = summary_text

    db.session.commit()
    logger.info(
        f"[metrics] ReportSummary written -> sim={simulation_id[:8]} | "
        f"runs={len(runs)} | avg_fact={avg_fact_score} | errors={len(errors)}"
    )
