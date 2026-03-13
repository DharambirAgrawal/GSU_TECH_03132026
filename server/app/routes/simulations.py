from __future__ import annotations

import threading
from datetime import datetime, timezone

from flask import current_app
from flask import Blueprint, jsonify, request
from pydantic import BaseModel, ValidationError, field_validator

from app.extensions import db
from app.models.simulation import Simulation
from app.services.auth_service import require_company_session
from app.tasks.simulations import run_agentic_geo_automation

bp = Blueprint("simulations", __name__)


class StartSimulationRequest(BaseModel):
    selection_id: str

    @field_validator("selection_id")
    @classmethod
    def selection_id_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("selection_id cannot be blank.")
        return value.strip()


def _parse_body(model_class):
    try:
        instance = model_class.model_validate(request.get_json(force=True) or {})
        return instance, None
    except ValidationError as exc:
        return None, (jsonify({"success": False, "errors": exc.errors()}), 400)


def _run_simulation_locally(flask_app, simulation_id: str) -> None:
    """Fallback executor used when Celery broker/worker is unavailable."""
    with flask_app.app_context():
        try:
            run_agentic_geo_automation.run(simulation_id)
        except Exception:
            simulation = Simulation.query.filter_by(id=simulation_id).first()
            if simulation is not None:
                simulation.status = "failed"
                simulation.time_ended = datetime.now(timezone.utc)
                db.session.commit()


@bp.route("/simulations", methods=["POST"])
def start_simulation():
    """Trigger simulation processing in Celery for an existing selection."""
    try:
        user, company = require_company_session(request)
    except PermissionError as exc:
        return jsonify({"success": False, "message": str(exc)}), 401

    body, err = _parse_body(StartSimulationRequest)
    if err:
        return err

    simulation = Simulation.query.filter_by(
        id=body.selection_id,
        company_id=company.id,
    ).first()

    if simulation is None:
        return jsonify({"success": False, "message": "Simulation not found."}), 404

    simulation.status = "queued"
    db.session.commit()

    try:
        async_result = run_agentic_geo_automation.delay(simulation.id)
        task_id = async_result.id
        mode = "celery"
    except Exception:
        app_obj = current_app._get_current_object()
        threading.Thread(
            target=_run_simulation_locally,
            args=(app_obj, simulation.id),
            daemon=True,
        ).start()
        task_id = f"local-{simulation.id}"
        mode = "local-thread"

    return (
        jsonify(
            {
                "success": True,
                "message": "Simulation started.",
                "selection_id": simulation.id,
                "task_id": task_id,
                "mode": mode,
            }
        ),
        202,
    )
