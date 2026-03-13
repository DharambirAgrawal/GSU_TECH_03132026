from __future__ import annotations

import logging
from urllib.parse import urlparse

from app.extensions import db
from app.models.simulation import Prompt, PromptModelRun, Simulation
from app.services.emailing import send_email
from app.services.metrices_generator import analyze_llm_response, generate_report_summary
from app.utils.llm_clients import query_all_llms
from app.utils.query_generator import COMPANY_PROFILES

logger = logging.getLogger(__name__)


def _normalize_domain(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    if not text:
        return ""
    parsed = urlparse(text if "://" in text else f"https://{text}")
    host = parsed.hostname or text
    return host.removeprefix("www.")


def agentic_geo_automation(
    simulation_id: str,
    recipient_email: str | None,
    frontend_base_url: str,
) -> dict[str, object]:
    """Run full simulation automation: query all LLMs, compute metrics, write summary."""
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
        "[automation] Starting simulation %s with %s prompts",
        simulation_id,
        len(prompts),
    )

    for prompt in prompts:
        processed_prompts += 1
        responses = query_all_llms(prompt.text, search=True)

        for model_name, response in responses.items():
            content = (response.content or "").strip()

            if content.startswith("[ERROR]"):
                db.session.add(
                    PromptModelRun(
                        simulation_id=simulation_id,
                        prompt_id=prompt.id,
                        model_name=model_name,
                        success_or_failed="failed",
                        failure_reason=content,
                        mitigation="Retry this model run after rate limits clear or credentials are fixed.",
                        citations_found_count=0,
                        dead_links_count=0,
                    )
                )
                db.session.commit()
                model_runs_created += 1
                continue

            try:
                analyze_llm_response(
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
                model_runs_created += 1
            except Exception as exc:
                logger.exception(
                    "[automation] analyze_llm_response failed | sim=%s prompt=%s model=%s",
                    simulation_id,
                    prompt.id,
                    model_name,
                )
                db.session.rollback()
                db.session.add(
                    PromptModelRun(
                        simulation_id=simulation_id,
                        prompt_id=prompt.id,
                        model_name=model_name,
                        success_or_failed="failed",
                        failure_reason=str(exc)[:2000],
                        mitigation="Inspect server logs for stack trace and rerun simulation.",
                        citations_found_count=0,
                        dead_links_count=0,
                    )
                )
                db.session.commit()
                model_runs_created += 1

    generate_report_summary(simulation_id)

    email_sent = False
    if recipient_email:
        login_url = f"{frontend_base_url.rstrip('/')}/login"
        message = (
            "Your simulation has completed.\n\n"
            f"Simulation ID: {simulation_id}\n"
            f"Prompts processed: {processed_prompts}\n"
            f"Model runs analyzed: {model_runs_created}\n"
            "Please login to view your data.\n"
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

    return {
        "simulation_id": simulation_id,
        "processed_prompts": processed_prompts,
        "model_runs_created": model_runs_created,
        "delay_seconds": 0,
        "email_sent": email_sent,
    }
