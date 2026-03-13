from __future__ import annotations

import random
import time

from app.services.emailing import send_email


def agentic_geo_automation(
    simulation_id: str,
    recipient_email: str | None,
    frontend_base_url: str,
) -> dict[str, object]:
    """Temporary automation placeholder used by Celery workers."""
    #     def query_all_llms(
    #     query: str,
    #     search: bool = False,
    #     platforms: Optional[list[str]] = None,
    # ) -> dict[str, LLMResponse]:
    email_sent = False
    if recipient_email:
        login_url = f"{frontend_base_url.rstrip('/')}/login"
        message = (
            "Your simulation has completed.\n\n"
            f"Selection ID: {simulation_id}\n"
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
        "email_sent": email_sent,
    }
