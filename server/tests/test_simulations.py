"""
tests/test_simulations.py
-----------------------------------------
Validation tests for:
    - CreateSimulationRequest Pydantic model
    - Simulation / Prompt DB model constraints
    - POST /api/agent/queries and GET /api/agent/queries/<id> routes
"""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from pydantic import ValidationError

from app import create_app
from app.extensions import db as _db
from app.models.auth import CompanyUser
from app.models.company import Company
from app.models.simulation import Prompt, Simulation
from app.routes.queries import CreateQueriesRequest


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _mock_auth(company: Company, user: CompanyUser):
    """Patch require_company_session to return the given (user, company) pair."""
    return patch(
        "app.routes.queries.require_company_session",
        return_value=(user, company),
    )


class _AppTestCase(unittest.TestCase):
    """Base class: spins up a fresh in-memory SQLite app for each test."""

    def setUp(self):
        self.app = create_app("testing")
        self.ctx = self.app.app_context()
        self.ctx.push()
        _db.create_all()
        self.db = _db
        self.client = self.app.test_client()

    def tearDown(self):
        _db.session.remove()
        _db.drop_all()
        self.ctx.pop()

    def _seed_company_and_user(self):
        company = Company(
            name="Acme Corp",
            slug="acme-corp",
            primary_domain="https://acme.example.com",
        )
        self.db.session.add(company)
        self.db.session.flush()
        user = CompanyUser(company_id=company.id, email="test@acme.example.com")
        self.db.session.add(user)
        self.db.session.commit()
        return company, user


# ---------------------------------------------------------------------------
# 1. Pydantic validation
# ---------------------------------------------------------------------------


class TestCreateSimulationRequestValidation(unittest.TestCase):
    def test_valid_minimal_payload(self):
        req = CreateQueriesRequest(product_specification="cloud storage", n_iteration=5)
        self.assertEqual(req.product_specification, "cloud storage")
        self.assertEqual(req.n_iteration, 5)
        self.assertIsNone(req.additional_detail)

    def test_whitespace_stripped_from_product_specification(self):
        req = CreateQueriesRequest(
            product_specification="  cloud storage  ", n_iteration=1
        )
        self.assertEqual(req.product_specification, "cloud storage")

    def test_optional_additional_detail(self):
        req = CreateQueriesRequest(
            product_specification="laptop",
            additional_detail="focus on battery life",
            n_iteration=3,
        )
        self.assertEqual(req.additional_detail, "focus on battery life")

    def test_blank_product_specification_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            CreateQueriesRequest(product_specification="   ", n_iteration=5)
        self.assertIn("product_specification", str(ctx.exception))

    def test_empty_product_specification_raises(self):
        with self.assertRaises(ValidationError):
            CreateQueriesRequest(product_specification="", n_iteration=5)

    def test_missing_product_specification_raises(self):
        with self.assertRaises(ValidationError):
            CreateQueriesRequest(n_iteration=5)  # type: ignore[call-arg]

    def test_n_iteration_zero_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            CreateQueriesRequest(product_specification="laptop", n_iteration=0)
        self.assertIn("n_iteration", str(ctx.exception))

    def test_n_iteration_negative_raises(self):
        with self.assertRaises(ValidationError):
            CreateQueriesRequest(product_specification="laptop", n_iteration=-5)

    def test_n_iteration_101_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            CreateQueriesRequest(product_specification="laptop", n_iteration=101)
        self.assertIn("n_iteration", str(ctx.exception))

    def test_n_iteration_100_is_valid(self):
        req = CreateQueriesRequest(product_specification="laptop", n_iteration=100)
        self.assertEqual(req.n_iteration, 100)

    def test_n_iteration_1_is_valid(self):
        req = CreateQueriesRequest(product_specification="laptop", n_iteration=1)
        self.assertEqual(req.n_iteration, 1)

    def test_missing_n_iteration_raises(self):
        with self.assertRaises(ValidationError):
            CreateQueriesRequest(product_specification="laptop")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# 2. DB model constraints
# ---------------------------------------------------------------------------


class TestSimulationDbModel(_AppTestCase):
    def test_create_simulation_with_required_fields(self):
        company, user = self._seed_company_and_user()
        now = datetime.now(timezone.utc)
        sim = Simulation(
            company_id=company.id,
            company_user_id=user.id,
            time_started=now,
            product_specification="enterprise firewall",
            n_iteration=5,
        )
        self.db.session.add(sim)
        self.db.session.commit()

        fetched = Simulation.query.get(sim.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.product_specification, "enterprise firewall")
        self.assertEqual(fetched.n_iteration, 5)
        self.assertEqual(fetched.status, "queued")
        self.assertEqual(fetched.company_id, company.id)

    def test_simulation_default_status_is_queued(self):
        company, user = self._seed_company_and_user()
        sim = Simulation(
            company_id=company.id,
            company_user_id=user.id,
            time_started=datetime.now(timezone.utc),
            product_specification="test product",
            n_iteration=1,
        )
        self.db.session.add(sim)
        self.db.session.commit()
        self.assertEqual(sim.status, "queued")

    def test_prompt_linked_to_simulation(self):
        company, user = self._seed_company_and_user()
        sim = Simulation(
            company_id=company.id,
            company_user_id=user.id,
            time_started=datetime.now(timezone.utc),
            product_specification="test product",
            n_iteration=2,
        )
        self.db.session.add(sim)
        self.db.session.flush()
        p1 = Prompt(
            simulation_id=sim.id, text="Who makes the best laptop?", prompt_order=0
        )
        p2 = Prompt(
            simulation_id=sim.id, text="Compare top laptop brands.", prompt_order=1
        )
        self.db.session.add_all([p1, p2])
        self.db.session.commit()

        self.assertEqual(len(sim.prompts), 2)
        self.assertEqual(sim.prompts[0].text, "Who makes the best laptop?")

    def test_deleting_simulation_cascades_to_prompts(self):
        company, user = self._seed_company_and_user()
        sim = Simulation(
            company_id=company.id,
            company_user_id=user.id,
            time_started=datetime.now(timezone.utc),
            product_specification="test product",
            n_iteration=1,
        )
        self.db.session.add(sim)
        self.db.session.flush()
        self.db.session.add(
            Prompt(simulation_id=sim.id, text="Sample prompt.", prompt_order=0)
        )
        self.db.session.commit()

        sim_id = sim.id
        self.db.session.delete(sim)
        self.db.session.commit()

        self.assertIsNone(Simulation.query.get(sim_id))
        self.assertEqual(Prompt.query.filter_by(simulation_id=sim_id).count(), 0)

    def test_simulation_requires_company_id(self):
        sim = Simulation(
            company_user_id=1,
            time_started=datetime.now(timezone.utc),
            product_specification="test",
            n_iteration=1,
        )
        self.db.session.add(sim)
        with self.assertRaises(Exception):
            self.db.session.commit()
        self.db.session.rollback()

    def test_simulation_requires_product_specification(self):
        company, user = self._seed_company_and_user()
        sim = Simulation(
            company_id=company.id,
            company_user_id=user.id,
            time_started=datetime.now(timezone.utc),
            n_iteration=1,
        )
        self.db.session.add(sim)
        with self.assertRaises(Exception):
            self.db.session.commit()
        self.db.session.rollback()


# ---------------------------------------------------------------------------
# 3. Route: POST /api/agent/queries
# ---------------------------------------------------------------------------


class TestPostSimulationsRoute(_AppTestCase):
    def test_no_auth_returns_401(self):
        with patch(
            "app.routes.queries.require_company_session",
            side_effect=PermissionError("No session."),
        ):
            response = self.client.post(
                "/api/agent/queries",
                data=json.dumps({"product_specification": "laptop", "n_iteration": 3}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.get_json()["success"])

    def test_missing_product_specification_returns_400(self):
        company, user = self._seed_company_and_user()
        with _mock_auth(company, user):
            response = self.client.post(
                "/api/agent/queries",
                data=json.dumps({"n_iteration": 5}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_blank_product_specification_returns_400(self):
        company, user = self._seed_company_and_user()
        with _mock_auth(company, user):
            response = self.client.post(
                "/api/agent/queries",
                data=json.dumps({"product_specification": "  ", "n_iteration": 5}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 400)

    def test_n_iteration_zero_returns_400(self):
        company, user = self._seed_company_and_user()
        with _mock_auth(company, user):
            response = self.client.post(
                "/api/agent/queries",
                data=json.dumps({"product_specification": "laptop", "n_iteration": 0}),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 400)

    def test_n_iteration_over_100_returns_400(self):
        company, user = self._seed_company_and_user()
        with _mock_auth(company, user):
            response = self.client.post(
                "/api/agent/queries",
                data=json.dumps(
                    {"product_specification": "laptop", "n_iteration": 101}
                ),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 400)

    def test_valid_payload_returns_201_with_prompts(self):
        company, user = self._seed_company_and_user()
        with _mock_auth(company, user):
            response = self.client.post(
                "/api/agent/queries",
                data=json.dumps(
                    {"product_specification": "enterprise laptop", "n_iteration": 3}
                ),
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertIsInstance(body["prompts"], list)
        self.assertEqual(len(body["prompts"]), 3)

    def test_prompt_count_matches_n_iteration(self):
        company, user = self._seed_company_and_user()
        with _mock_auth(company, user):
            response = self.client.post(
                "/api/agent/queries",
                data=json.dumps(
                    {"product_specification": "cloud storage", "n_iteration": 5}
                ),
                content_type="application/json",
            )
        self.assertEqual(len(response.get_json()["prompts"]), 5)

    def test_prompts_persisted_to_db(self):
        company, user = self._seed_company_and_user()
        with _mock_auth(company, user):
            response = self.client.post(
                "/api/agent/queries",
                data=json.dumps(
                    {"product_specification": "security software", "n_iteration": 4}
                ),
                content_type="application/json",
            )
        prompt_ids = [item["id"] for item in response.get_json()["prompts"]]
        persisted_prompts = Prompt.query.filter(Prompt.id.in_(prompt_ids)).count()
        self.assertEqual(persisted_prompts, 4)

    def test_simulation_persisted_to_db(self):
        existing_count = Simulation.query.count()
        company, user = self._seed_company_and_user()
        with _mock_auth(company, user):
            response = self.client.post(
                "/api/agent/queries",
                data=json.dumps(
                    {"product_specification": "network switch", "n_iteration": 2}
                ),
                content_type="application/json",
            )
        self.assertEqual(Simulation.query.count(), existing_count + 1)


# ---------------------------------------------------------------------------
# 4. Route: GET /api/agent/queries/<id>
# ---------------------------------------------------------------------------


class TestGetSimulationRoute(_AppTestCase):
    def _create_simulation(self, company, user, n=3):
        sim = Simulation(
            company_id=company.id,
            company_user_id=user.id,
            time_started=datetime.now(timezone.utc),
            product_specification="router hardware",
            n_iteration=n,
        )
        self.db.session.add(sim)
        self.db.session.flush()
        for i in range(n):
            self.db.session.add(
                Prompt(simulation_id=sim.id, text=f"Prompt {i}", prompt_order=i)
            )
        self.db.session.commit()
        return sim

    def test_no_auth_returns_401(self):
        with patch(
            "app.routes.queries.require_company_session",
            side_effect=PermissionError("No session."),
        ):
            response = self.client.get("/api/agent/queries/nonexistent-id")
        self.assertEqual(response.status_code, 401)

    def test_unknown_id_returns_404(self):
        company, user = self._seed_company_and_user()
        with _mock_auth(company, user):
            response = self.client.get(
                "/api/agent/queries/00000000-0000-0000-0000-000000000000"
            )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])

    def test_returns_prompts(self):
        company, user = self._seed_company_and_user()
        sim = self._create_simulation(company, user, n=3)
        with _mock_auth(company, user):
            response = self.client.get(f"/api/agent/queries/{sim.id}")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(len(body["prompts"]), 3)

    def test_prompts_returned_in_order(self):
        company, user = self._seed_company_and_user()
        sim = self._create_simulation(company, user, n=5)
        with _mock_auth(company, user):
            response = self.client.get(f"/api/agent/queries/{sim.id}")
        orders = [p["prompt_order"] for p in response.get_json()["prompts"]]
        self.assertEqual(orders, sorted(orders))

    def test_cross_company_isolation(self):
        company, user = self._seed_company_and_user()
        sim = self._create_simulation(company, user, n=1)

        other_company = Company(
            name="Other Corp",
            slug="other-corp",
            primary_domain="https://other.example.com",
        )
        self.db.session.add(other_company)
        self.db.session.flush()
        other_user = CompanyUser(
            company_id=other_company.id, email="user@other.example.com"
        )
        self.db.session.add(other_user)
        self.db.session.commit()

        with _mock_auth(other_company, other_user):
            response = self.client.get(f"/api/agent/queries/{sim.id}")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
