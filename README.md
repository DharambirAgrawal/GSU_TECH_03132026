# GEO Simulation Backend

Simple backend for running AI visibility simulations for a company.

It lets a company:
- register and log in with magic link auth
- generate a list of prompts for a simulation
- start async simulation runs across multiple LLMs
- store citations, errors, and fact-check results
- view dashboard/metrics data
- generate a department-specific PDF report

---

## 1) Tech Stack

- Python + Flask
- SQLAlchemy + Flask-Migrate
- SQLite in development
- Celery for async jobs (with local thread fallback)
- LLM clients: OpenAI, Anthropic, Perplexity, Gemini
- ReportLab for PDF generation

---

## 2) How the App Works

1. Company registers and sets its domain.
2. User requests a magic login link.
3. User verifies link and gets a session token.
4. User creates simulation prompts.
5. User starts simulation.
6. Background worker runs LLM checks and writes results.
7. Dashboard/metrics endpoints read those results.
8. PDF endpoint creates an actionable report for engineering or marketing.

---

## 3) Project Structure (Important Files)

- `run.py`: starts Flask app
- `config.py`: environment-based config (DB, Celery, keys)
- `app/__init__.py`: app factory + blueprint registration
- `app/routes/auth.py`: register, magic link, session endpoints
- `app/routes/queries.py`: create/get/cancel prompt sets
- `app/routes/simulations.py`: start simulation + generate PDF
- `app/routes/dashboard.py`: analytics payload for dashboard
- `app/routes/metrics.py`: cards and detail metrics endpoints
- `app/tasks/simulations.py`: Celery task wrapper
- `app/services/agentic_geo_automation.py`: main simulation pipeline
- `app/services/pdf_report_generator.py`: PDF generation logic
- `app/models/simulation.py`: simulation-related DB schema
- `tests/`: unittest test suite

---

## 4) API Overview

Base URL (local): `http://localhost:5000`

### Health
- `GET /api/health`

### Auth (`/api/auth`)
- `POST /register-company`
- `POST /request-magic-link`
- `POST /verify-magic-link`
- `GET /verify?token=...` (redirect flow)
- `GET /me`
- `POST /logout`

### Query Drafts (`/api/agent`)
- `POST /queries`
- `GET /queries/<simulation_id>`
- `POST /queries/cancel`

### Simulations + Reports (`/api/agents`)
- `POST /simulations`
- `POST /pdfs`

### Analytics
- `GET /api/dashboard/analytics`
- `GET /api/metrics/dashboard`
- `GET /api/metrics/accuracy`
- `GET /api/metrics/visibility`
- `GET /api/metrics/competitors`
- `GET /api/metrics/actions`

Most endpoints require:
- `Authorization: Bearer <session_token>`

---

## 5) Environment Variables

Create a `.env` file in the server folder.

Required or commonly used:

- `FLASK_ENV=development`
- `SECRET_KEY=your_secret`
- `DATABASE_URL=sqlite:///vigil_dev.db`
- `FRONTEND_BASE_URL=http://localhost:3000`
- `BACKEND_BASE_URL=http://localhost:5000`

- `CELERY_BROKER_URL=redis://localhost:6379/0`
- `CELERY_RESULT_BACKEND=redis://localhost:6379/0`

- `OPENAI_API_KEY=...`
- `ANTHROPIC_API_KEY=...`
- `PERPLEXITY_API_KEY=...`
- `GOOGLE_API_KEY=...`

- `POWERAUTOMATE_EMAIL_API_URL=...`

Notes:
- In development, tables can auto-create on startup.
- If Celery is not available, simulation route falls back to local thread execution.

---

## 6) Run Locally

From the repository root, start both services:

macOS/Linux (or Git Bash):

```bash
bash run.sh
```

Windows PowerShell:

```powershell
./run.ps1
```

Windows CMD:

```bat
run.bat
```

This starts both services:
- Client: `http://localhost:5173`
- Server: `http://localhost:5000`

Other modes:

macOS/Linux:

```bash
bash run.sh server
bash run.sh client
bash run.sh worker
```

Windows PowerShell:

```powershell
./run.ps1 server
./run.ps1 client
./run.ps1 worker
```

---

## 7) Run Tests

```bash
python -m unittest discover -s tests
```

---

## 8) Judge Notes

If you are evaluating this backend quickly:

1. Check health route first: `/api/health`
2. Register company and complete magic-link auth
3. Create queries with `/api/agent/queries`
4. Start run with `/api/agents/simulations`
5. Review metrics at `/api/dashboard/analytics` and `/api/metrics/*`
6. Generate a PDF with `/api/agents/pdfs`

This gives a full end-to-end validation of the core flow.
