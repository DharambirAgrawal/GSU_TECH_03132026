from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from pydantic import BaseModel, ValidationError, field_validator

from app.extensions import db
from app.models.simulation import Prompt, Simulation
from app.services.auth_service import require_company_session
from app.utils.query_generator import generate_queries

bp = Blueprint("queries", __name__)


class CreateQueriesRequest(BaseModel):
    product_specification: str
    additional_detail: str | None = None
    n_iteration: int

    @field_validator("product_specification")
    @classmethod
    def product_spec_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("product_specification cannot be blank.")
        return value.strip()

    @field_validator("n_iteration")
    @classmethod
    def n_iteration_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("n_iteration must be greater than 0.")
        if value > 100:
            raise ValueError("n_iteration must be 100 or less.")
        return value


class CancelQueriesRequest(BaseModel):
    simulation_id: str

    @field_validator("simulation_id")
    @classmethod
    def simulation_id_not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("simulation_id cannot be blank.")
        return value.strip()


def _parse_body(model_class):
    try:
        instance = model_class.model_validate(request.get_json(force=True) or {})
        return instance, None
    except ValidationError as exc:
        return None, (jsonify({"success": False, "errors": exc.errors()}), 400)


def _fallback_prompt_texts(
    product_specification: str, additional_detail: str | None, count: int
) -> list[str]:
    """Generate deterministic fallback prompts when company is not in query profiles."""
    detail_suffix = (
        f" considering {additional_detail.strip()}" if additional_detail else ""
    )
    base_templates = [
        f"What are the best options for {product_specification}{detail_suffix}?",
        f"Compare top providers for {product_specification}{detail_suffix}.",
        f"What should I watch out for when choosing {product_specification}{detail_suffix}?",
        f"Which company is most reliable for {product_specification}{detail_suffix}?",
        f"What are common mistakes when buying {product_specification}{detail_suffix}?",
    ]

    prompts: list[str] = []
    idx = 0
    while len(prompts) < count:
        template = base_templates[idx % len(base_templates)]
        prompts.append(f"{template} (iteration {len(prompts) + 1})")
        idx += 1
    return prompts


@bp.route("/queries", methods=["POST"])
def create_queries():
    """
    Generate and persist prompts for a future simulation.

    Auth required via Bearer token.

    Request body:
      - product_specification (str)
      - additional_detail (str, optional)
      - n_iteration (int)
    """
    try:
        user, company = require_company_session(request)
    except PermissionError as exc:
        return jsonify({"success": False, "message": str(exc)}), 401

    body, err = _parse_body(CreateQueriesRequest)
    if err:
        return err

    now = datetime.now(timezone.utc)
    simulation = Simulation(
        company_id=company.id,
        company_user_id=user.id,
        time_started=now,
        status="queued",
        product_specification=body.product_specification,
        n_iteration=body.n_iteration,
        additional_detail=body.additional_detail,
        about_company=company.about_company,
        contact_email=user.email,
        url=company.primary_domain,
        time_created=now,
    )

    # Primary prompt generation path uses utils/query_generator profiles.
    try:
        generated = generate_queries(
            company_name=company.name,
            product=body.product_specification,
            num_queries=body.n_iteration,
        )
        prompt_texts = [item.text for item in generated]
    except Exception as e:
        import logging
        logging.error(f"Error generating queries dynamically: {e}")
        # Fallback keeps route functional for companies not yet in query profiles.
        prompt_texts = _fallback_prompt_texts(
            product_specification=body.product_specification,
            additional_detail=body.additional_detail,
            count=body.n_iteration,
        )

    db.session.add(simulation)
    db.session.flush()

    for index, prompt_text in enumerate(prompt_texts):
        db.session.add(
            Prompt(
                simulation_id=simulation.id,
                text=prompt_text,
                prompt_order=index,
            )
        )

    db.session.commit()

    # Re-query prompts in order so IDs are included in the response.
    saved_prompts = (
        Prompt.query.filter_by(simulation_id=simulation.id)
        .order_by(Prompt.prompt_order)
        .all()
    )

    return (
        jsonify(
            {
                "success": True,
                "simulation_id": simulation.id,
                "prompts": [
                    {
                        "id": p.id,
                        "simulation_id": p.simulation_id,
                        "prompt_order": p.prompt_order,
                        "text": p.text,
                    }
                    for p in saved_prompts
                ],
            }
        ),
        201,
    )


@bp.route("/queries/<string:simulation_id>", methods=["GET"])
def get_queries(simulation_id: str):
    """
    Fetch persisted prompts for a simulation draft.

    Auth required via Bearer token. The simulation must belong to the
    authenticated user's company.
    """
    try:
        user, company = require_company_session(request)
    except PermissionError as exc:
        return jsonify({"success": False, "message": str(exc)}), 401

    simulation = Simulation.query.filter_by(
        id=simulation_id, company_id=company.id
    ).first()

    if simulation is None:
        return jsonify({"success": False, "message": "Simulation not found."}), 404

    prompts = (
        Prompt.query.filter_by(simulation_id=simulation.id)
        .order_by(Prompt.prompt_order)
        .all()
    )

    return (
        jsonify(
            {
                "success": True,
                "prompts": [
                    {
                        "id": p.id,
                        "prompt_order": p.prompt_order,
                        "text": p.text,
                        "time_created": (
                            p.time_created.isoformat() if p.time_created else None
                        ),
                    }
                    for p in prompts
                ],
            }
        ),
        200,
    )


@bp.route("/queries/cancel", methods=["POST"])
def cancel_queries():
    """Cancel query generation result by deleting its simulation draft and prompts."""
    try:
        user, company = require_company_session(request)
    except PermissionError as exc:
        return jsonify({"success": False, "message": str(exc)}), 401

    body, err = _parse_body(CancelQueriesRequest)
    if err:
        return err

    simulation = Simulation.query.filter_by(
        id=body.simulation_id, company_id=company.id
    ).first()

    if simulation is None:
        return jsonify({"success": False, "message": "Simulation not found."}), 404

    deleted_prompt_count = len(simulation.prompts)
    db.session.delete(simulation)
    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "message": "Simulation cancelled and deleted.",
                "simulation_id": body.simulation_id,
                "deleted_prompt_count": deleted_prompt_count,
            }
        ),
        200,
    )
