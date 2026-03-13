from __future__ import annotations

from datetime import datetime, timezone

from flask import current_app

from app.celery_app import celery_app
from app.extensions import db
from app.models.simulation import Simulation
from app.services.agentic_geo_automation import agentic_geo_automation


@celery_app.task(name="simulations.run_agentic_geo_automation")
def run_agentic_geo_automation(simulation_id: str) -> dict[str, object]:
    simulation = Simulation.query.get(simulation_id)
    if simulation is None:
        return {"simulation_id": simulation_id, "status": "missing"}

    simulation.status = "running"
    db.session.commit()

    try:
        result = agentic_geo_automation(
            simulation_id=simulation.id,
            recipient_email=simulation.contact_email,
            frontend_base_url=current_app.config.get("FRONTEND_BASE_URL", ""),
        )

        simulation.status = "completed"
        simulation.time_ended = datetime.now(timezone.utc)
        db.session.commit()
    except Exception:
        db.session.rollback()
        simulation = Simulation.query.get(simulation_id)
        if simulation is not None:
            simulation.status = "failed"
            simulation.time_ended = datetime.now(timezone.utc)
            db.session.commit()
        raise

    return {
        "simulation_id": simulation.id,
        "status": simulation.status,
        "delay_seconds": result.get("delay_seconds", 0),
        "email_sent": result.get("email_sent", False),
        "processed_prompts": result.get("processed_prompts", 0),
        "model_runs_created": result.get("model_runs_created", 0),
    }
