# VIGIL Backend — Manual Run + Company-Domain Magic Link Architecture

## Stack
- Flask API
- SQLAlchemy ORM + Flask-Migrate
- SQLite for development (PostgreSQL-ready)
- Pydantic for request validation
- LLM clients (OpenAI / Anthropic / others)

---

## 1) Product Flow (Updated)

This backend is now **manual-run driven**.

There are **no daily/weekly scheduler automations** that run the entire app globally.
Everything starts only when an authenticated company user clicks from frontend.

### End-to-end flow
1. Company registers with:
   - company name
   - company URL
   - about company (optional)
2. Backend extracts and auto-approves company login domain (for now).
   - Example: `amazon.com`
3. Any user with `*@amazon.com` can request a magic link.
4. User clicks magic link, receives session, and opens company dashboard.
5. User chooses topic + number of prompts (e.g., 50), edits any prompts, then clicks Start.
6. Backend immediately accepts request, enqueues async run, and returns success.
7. Run executes in background and creates a history entry.
8. All users in same company see the same dashboard + same run history.

---

## 2) Multi-tenant Access Model

Tenant model is **company-scoped**, not user-scoped.

- Company is the data boundary.
- Many users can belong to one company.
- Access is granted by email domain allowlist.
- Dashboard state and history are shared for all users in that company.

### Example
- Allowed domain: `ebay.com`
- `user1@ebay.com`, `ops@ebay.com`, `leader@ebay.com`
- All authenticate into the **same company dashboard** and view same run history.

---

## 3) Authentication (Magic Link)

### Registration
`POST /api/auth/register-company`

Input:
- `company_name`
- `company_url`
- `about_company` (optional)
- `contact_email`

Backend actions:
- Creates `Company`
- Creates primary `CompanyDomain`
- Creates/updates `CompanyConfig`
- Creates initial `CompanyUser` (owner)

### Request link
`POST /api/auth/request-magic-link`

Input:
- `email`

Backend actions:
- Verifies email domain is allowed
- Creates one-time token (`MagicLinkToken`)
- Sends link via email provider

### Verify link
`POST /api/auth/verify-magic-link`

Input:
- `token`

Backend actions:
- Verifies token (unused, unexpired)
- Marks token used
- Creates `UserSession`
- Returns session token and company context

### Session profile
`GET /api/auth/me`

Returns:
- authenticated user info
- company info

---

## 4) Manual Run Lifecycle

### A) Generate prompts
`POST /api/runs/generate-prompts`

Input:
- `topic` (example: `Laptop`)
- `query_count` (example: `50`)

Backend:
- builds company-aware prompts
- creates draft run (`QueryBatchRun`) + items (`QueryBatchItem`)
- returns editable prompt list

### B) Edit prompts
`PATCH /api/runs/<run_id>/queries`

Input:
- list of edited queries

Backend:
- replaces/reorders run items
- records editor user id

### C) Start run (async)
`POST /api/runs/<run_id>/start`

Backend:
- returns immediate success (`queued`)
- worker executes queries in background
- updates run status/progress counters

### D) Poll status
`GET /api/runs/<run_id>/status`

Returns:
- status
- completed/failed counts
- progress percentage

### E) View history
`GET /api/runs/history`
`GET /api/runs/history/<run_id>`

Returns:
- all historical runs for company
- query-level outcomes
- before/after snapshots for comparison

---

## 5) Data Models (New/Updated)

## Company-related
- `Company` (updated)
  - added `about_company`
  - added `approved_email_domain`
  - added `registration_status`
- `CompanyConfig` (updated)
  - manual-run controls (`default_query_count`, `max_query_count`)

## Auth models
- `CompanyDomain`
- `CompanyUser`
- `MagicLinkToken`
- `UserSession`

## Run history models
- `QueryBatchRun`
- `QueryBatchItem`

## Existing execution models (reused)
- `QueryTemplate`
- `QueryRun` (now can link to `batch_run_id` / `batch_item_id`)
- `AccuracyCheck`
- `FactualError`
- `ContentFix`

---

## 6) Folder Structure (Updated)

```text
server/
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── company.py
│   │   ├── auth.py
│   │   ├── run_history.py
│   │   ├── query.py
│   │   ├── accuracy.py
│   │   ├── crawl.py
│   │   ├── content.py
│   │   ├── competitor.py
│   │   ├── source.py
│   │   └── ethics.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── runs.py
│   │   ├── query_tester.py
│   │   ├── dashboard.py
│   │   ├── visibility.py
│   │   ├── accuracy.py
│   │   ├── competitors.py
│   │   ├── actions.py
│   │   ├── crawl.py
│   │   └── ethics.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── run_orchestrator.py
│   │   ├── query_runner.py
│   │   ├── fact_checker.py
│   │   ├── crawler.py
│   │   ├── content_generator.py
│   │   ├── root_cause.py
│   │   └── scoring.py
│   ├── jobs/
│   │   └── __init__.py   # legacy namespace only (no scheduled automations)
│   └── utils/
│       ├── llm_clients.py
│       └── schema_validator.py
├── migrations/
├── tests/
├── config.py
├── run.py
└── requirements.txt
```

---

## 7) Background Processing Strategy (No Scheduler)

There is no APScheduler-driven global loop.

Background execution is request-driven:
- frontend start action creates queued run
- orchestrator starts worker thread/job for that run
- worker updates status and history

For production scale, switch executor to Celery/RQ/SQS without changing API contracts.

---

## 8) API Contract Summary

### Auth
- `POST /api/auth/register-company`
- `POST /api/auth/request-magic-link`
- `POST /api/auth/verify-magic-link`
- `GET /api/auth/me`
- `POST /api/auth/logout`

### Runs + History
- `POST /api/runs/generate-prompts`
- `PATCH /api/runs/<run_id>/queries`
- `POST /api/runs/<run_id>/start`
- `GET /api/runs/<run_id>/status`
- `GET /api/runs/history`
- `GET /api/runs/history/<run_id>`

### Existing Analytics
- `GET /api/dashboard/...`
- `GET /api/visibility/...`
- `GET /api/accuracy/...`
- `GET /api/competitors/...`
- `GET /api/actions/...`
- `GET /api/crawl/...`
- `GET /api/ethics/...`

---

## 9) Notes for Frontend Team

- Login UX can be one field + button:
  - email input
  - “Send magic link” button
- After link verify, use session token in `Authorization: Bearer ...`.
- Run flow UX should be:
  1) choose topic + count
  2) edit prompts
  3) start
  4) poll status
  5) view history detail

---

## 10) Next Backend Implementation Steps

1. Implement `auth_service.py` token issuance + email provider integration.
2. Implement `run_orchestrator.py` threaded worker execution path.
3. Register new blueprints in app factory.
4. Add migration for new auth/history tables.
5. Add integration tests for auth and run lifecycle.
