from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import BaseModel, ValidationError, field_validator

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

    try:
        async_result = run_agentic_geo_automation.delay(simulation.id)
    except Exception:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Failed to enqueue simulation processing.",
                }
            ),
            500,
        )

    return (
        jsonify(
            {
                "success": True,
                "message": "Simulation started.",
                "selection_id": simulation.id,
                "task_id": async_result.id,
            }
        ),
        202,
    )
