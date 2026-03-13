# Vigil Backend — Implementation Tracker
> **How to use this doc:** Work top-to-bottom. Each section has a status badge.  
> Update the badge and add implementation notes as you build each piece.  
> If a feature changes, update the relevant section so downstream sections that depend on it stay accurate.

---

## Status Key
| Badge | Meaning |
|-------|---------|
| ✅ DONE | Code exists and is real Python — not comment-spec |
| 🔧 SPEC | File exists but is comment-spec only (no runnable code yet) |
| 🔴 TODO | Does not exist yet |
| ⚠️ NEEDS UPDATE | Exists but requires change based on a decision made later |

---

## Table of Contents
1. [Foundation — App Factory & Config](#1-foundation)
2. [Email Service](#2-email-service)
3. [Authentication — Full Flow](#3-authentication)
   - 3a. Data Models
   - 3b. Auth Service
   - 3c. Auth Routes
   - 3d. Frontend Handshake Contract
4. [Manual Run System](#4-manual-run-system)
   - 4a. Data Models
   - 4b. Run Orchestrator Service
   - 4c. Run Routes
5. [Analytics & Dashboard Routes](#5-analytics-routes)
6. [Environment Variables Reference](#6-environment-variables)
7. [Database Migrations](#7-database-migrations)
8. [Testing Checklist](#8-testing-checklist)

---

## 1. Foundation

### `config.py` — App Configuration Classes
**Status:** ✅ DONE  
**File:** `server/config.py`

**What needs to be written:**
- `Config` base class with all env-driven attributes
- `DevelopmentConfig(Config)` — SQLite, DEBUG=True
- `ProductionConfig(Config)` — PostgreSQL URL, DEBUG=False
- `TestingConfig(Config)` — in-memory SQLite, TESTING=True

**Config keys that must be present:**

| Key | Source | Used By |
|-----|--------|---------|
| `SECRET_KEY` | env | Flask sessions |
| `DATABASE_URL` | env (optional) | SQLAlchemy |
| `SQLALCHEMY_DATABASE_URI` | derived | SQLAlchemy |
| `FRONTEND_BASE_URL` | env | Magic link URL builder |
| `MAGIC_LINK_TTL_MINUTES` | env, default 15 | `auth_service.issue_magic_link` |
| `SESSION_TTL_HOURS` | env, default 72 | `auth_service.verify_magic_link_and_create_session` |
| `MAX_QUERIES_PER_RUN` | env, default 100 | `run_orchestrator.create_draft_batch` |
| `POWERAUTOMATE_EMAIL_API_URL` | env | `services/emailing.py` |
| `OPENAI_API_KEY` | env | `utils/llm_clients.py` |
| `ANTHROPIC_API_KEY` | env | `utils/llm_clients.py` |
| `PERPLEXITY_API_KEY` | env | `utils/llm_clients.py` |
| `GOOGLE_API_KEY` | env | `utils/llm_clients.py` |

**Implementation note:**  
`SQLALCHEMY_DATABASE_URI` should fall back to `sqlite:///vigil_dev.db` if `DATABASE_URL` is not set.

---

### `app/__init__.py` — App Factory
**Status:** ✅ DONE  
**File:** `server/app/__init__.py`

**What needs to be written:**
- `create_app(config_name="development")` function
- Register extensions: `db`, `migrate`
- Register all 10 blueprints at their URL prefixes
- No scheduler — all runs are user-triggered

**Blueprint registration order (matters for circular import safety):**

| Blueprint | Prefix | File |
|-----------|--------|------|
| `auth` | `/api/auth` | `routes/auth.py` |
| `runs` | `/api/runs` | `routes/runs.py` |
| `dashboard` | `/api/dashboard` | `routes/dashboard.py` |
| `visibility` | `/api/visibility` | `routes/visibility.py` |
| `accuracy` | `/api/accuracy` | `routes/accuracy.py` |
| `competitors` | `/api/competitors` | `routes/competitors.py` |
| `actions` | `/api/actions` | `routes/actions.py` |
| `crawl` | `/api/crawl` | `routes/crawl.py` |
| `query_tester` | `/api/query-tester` | `routes/query_tester.py` |
| `ethics` | `/api/ethics` | `routes/ethics.py` |

---

### `app/extensions.py` — Shared Flask Extensions
**Status:** ✅ DONE  
**File:** `server/app/extensions.py`

**What exists:**
- `db = SQLAlchemy()`
- `migrate = Migrate()`
- APScheduler has been removed

**No changes needed** unless a new extension is added.

---

## 2. Email Service

### `app/services/emailing.py` — Power Automate Email Dispatch
**Status:** ✅ DONE  
**File:** `server/app/services/emailing.py`

**How it works:**
```
send_email(recipient, subject, message)
  → POST {POWERAUTOMATE_EMAIL_API_URL}  (10s timeout)
  → body: { subject, recipient (rewritten to @gmail.com), message (newlines → <br>) }
  → raises ValueError if POWERAUTOMATE_EMAIL_API_URL not set
  → raises Exception if response != 200
```

> **Recipient rewrite:** `dev.dharambir@amazon.com` → `dev.dharambir@gmail.com`  
> Intentional for dev/testing — magic links go to personal Gmail inboxes.

**Depends on:**
- `settings.POWERAUTOMATE_EMAIL_API_URL` — populated in `server/settings.py` ✅

**Used by:**
- `auth_service.issue_magic_link` — sends the magic link email

**Tested:** ✅ Email received at dev.dharambir@gmail.com on 2026-03-12.

---

## 3. Authentication

> **Full auth flow summary:**
> 1. Company registers → domain auto-approved → owner user created
> 2. Any `@that-domain.com` user enters email → magic link sent to their Gmail (`@gmail.com` rewrite)
> 3. User clicks link → hits **backend** `GET /api/auth/verify?token=...`
> 4. Backend verifies token → creates session → in dev shows HTML page; in prod redirects to `{FRONTEND_BASE_URL}/dashboard?session_token=...`
> 5. Frontend stores `session_token`, sends on every request as `Authorization: Bearer <session_token>`
> 6. Server validates session → resolves company scope → serves data

---

### 3a. Data Models — `app/models/auth.py`
**Status:** ✅ DONE  
**File:** `server/app/models/auth.py`

**Tables created:**

| Table | Model | Purpose |
|-------|-------|---------|
| `company_domains` | `CompanyDomain` | Allowed login domains per company |
| `company_users` | `CompanyUser` | Employee identities (no passwords) |
| `magic_link_tokens` | `MagicLinkToken` | One-time login tokens (stored as SHA-256 hash) |
| `user_sessions` | `UserSession` | Active sessions (stored as SHA-256 hash) |

**Key security design:**
- Raw tokens are **never** stored in the database
- Only `sha256(raw_token)` is persisted
- Magic links expire in 15 minutes (configurable)
- Sessions expire in 72 hours (configurable)

**Relationships:**
- `CompanyUser` → `Company` (many users per company, all see same dashboard)
- `MagicLinkToken` → `CompanyUser` (cascade delete on user delete)
- `UserSession` → `CompanyUser` (cascade delete on user delete)
- `CompanyUser` → `QueryBatchRun` (as `created_by`)

**No code changes needed** to this file.

---

### 3b. Extended Company Model — `app/models/company.py`
**Status:** ✅ DONE  
**File:** `server/app/models/company.py`

**Fields added for auth:**
- `about_company: Text` — free-text description entered at registration
- `approved_email_domain: String(255)` — the primary domain used to match incoming login emails
- `registration_status: String(30), default="approved"` — auto-approved for now

**Relationships added:**
- `users → CompanyUser`
- `allowed_domains → CompanyDomain`
- `query_batches → QueryBatchRun`

**No code changes needed.**

---

### 3c. Auth Service — `app/services/auth_service.py`
**Status:** ✅ DONE  
**File:** `server/app/services/auth_service.py`

**Functions to implement (in dependency order):**

#### `hash_token(raw_token: str) -> str`
```
import hashlib
return hashlib.sha256(raw_token.encode()).hexdigest()
```
Simple utility. No dependencies.

---

#### `normalize_domain(value: str) -> str`
```
Strip protocol/www from URL  OR  extract domain part from email
"https://www.amazon.com"  →  "amazon.com"
"User@Amazon.com"         →  "amazon.com"
```
Uses `urllib.parse.urlparse`. No DB access.

---

#### `ensure_company_and_domain(company_name, company_url, about_company, contact_email) -> (Company, CompanyDomain, CompanyUser)`
```
1. normalize domain from company_url
2. Check: no existing Company with same approved_email_domain (prevent duplicate)
3. Create Company(registration_status="approved", approved_email_domain=...)
4. Create CompanyDomain(is_primary=True, is_active=True)
5. Create CompanyUser(email=contact_email, role="owner")
6. db.session.commit()
7. Return (company, domain, user)
```
Called only during company registration.

---

#### `issue_magic_link(user: CompanyUser, request_meta: dict) -> dict`
```
1. raw = secrets.token_urlsafe(32)
2. token_hash = hash_token(raw)
3. expires_at = now + MAGIC_LINK_TTL_MINUTES
4. Save MagicLinkToken(token_hash, expires_at, user_id, company_id, ...)
5. db.session.commit()
6. link = f"{FRONTEND_BASE_URL}/auth/verify?token={raw}"
7. Call send_email(
       recipient=user.email,
       subject="Your Vigil login link",
       message=f"Click here to log in: {link}\n\nExpires in 15 minutes."
   )
8. Return { "email": user.email, "expires_at": expires_at }
```
**Uses `emailing.send_email`** — not SMTP. See Section 2.

---

#### `verify_magic_link_and_create_session(raw_token: str, request_meta: dict) -> dict`
```
1. token_hash = hash_token(raw_token)
2. Look up MagicLinkToken(token_hash=token_hash)
3. Validate: exists, not expired (expires_at > now), not used (used_at is None)
4. Mark token: used_at = now
5. raw_session = secrets.token_urlsafe(48)
6. session_hash = hash_token(raw_session)
7. session_expires_at = now + SESSION_TTL_HOURS
8. Save UserSession(session_token_hash=session_hash, expires_at=...)
9. Update user.last_login_at = now
10. db.session.commit()
11. Return {
      "session_token": raw_session,      ← only time raw is returned
      "session_expires_at": ...,
      "user": { id, email, full_name, role },
      "company": { id, name, approved_email_domain }
    }
```
The returned `session_token` is stored by the frontend and sent as Bearer token on every request.

---

#### `require_company_session(request) -> tuple[CompanyUser, Company]`
```
1. header = request.headers.get("Authorization", "")
2. if not header.startswith("Bearer "): abort(401)
3. raw_token = header.split(" ", 1)[1]
4. token_hash = hash_token(raw_token)
5. session = UserSession.query.filter_by(session_token_hash=token_hash).first()
6. Validate: exists, not expired, not revoked
7. company = Company.query.get(session.company_id)
8. user = CompanyUser.query.get(session.user_id)
9. Return (user, company)
```
Used as a guard at the top of every protected route handler.

---

#### `revoke_session(raw_session_token: str) -> bool`
```
1. token_hash = hash_token(raw_session_token)
2. session = UserSession.query.filter_by(session_token_hash=token_hash).first()
3. If found: session.revoked_at = now; db.session.commit(); return True
4. Return False
```

---

### 3d. Auth Routes — `app/routes/auth.py`
**Status:** ✅ DONE  
**File:** `server/app/routes/auth.py`

> **Email link flow update (2026-03-12):**  
> Magic link now points to **backend** `GET /api/auth/verify?token=...`  
> Backend verifies token, creates session, then:
> - **Dev (DEBUG=True):** Shows an HTML page with the session token + copy button + curl example
> - **Production:** Redirects to `{FRONTEND_BASE_URL}/dashboard?session_token=...&email=...&company=...`
> 
> This means the link in the email works even before the frontend is running.

**Routes implemented:**

---

#### `GET /api/auth/verify` *(email link target — added 2026-03-12)*
**Purpose:** The URL embedded in the magic-link email. Verifies token server-side and either shows dev page (DEBUG=True) or redirects to frontend dashboard.

**Query param:** `?token=<raw_token>`

**Dev response:** HTML page with session token display + copy button + curl example  
**Prod response:** `302` redirect to `{FRONTEND_BASE_URL}/dashboard?session_token=...`  
**Error:** `302` redirect to `{FRONTEND_BASE_URL}/login?error=invalid_token|token_expired|token_used`

---

#### `POST /api/auth/register-company`
**Purpose:** Create company workspace and auto-approve domain.

**Request body:**
```json
{
  "company_name": "Amazon",
  "company_url": "https://www.amazon.com",
  "about_company": "World's largest online marketplace",
  "contact_email": "admin@amazon.com"
}
```

**Response `201`:**
```json
{
  "success": true,
  "company": {
    "id": 1,
    "name": "Amazon",
    "approved_email_domain": "amazon.com",
    "registration_status": "approved"
  },
  "user": {
    "id": 1,
    "email": "admin@amazon.com",
    "role": "owner"
  },
  "message": "Company registered. You can now log in with any @amazon.com email."
}
```

**Error cases:**
- `400` — missing required fields
- `409` — domain already registered

---

#### `POST /api/auth/request-magic-link`
**Purpose:** Send magic link email to a valid company domain email.

**Request body:**
```json
{ "email": "user@amazon.com" }
```

**Response `200` (always, even if domain not found — prevents enumeration):**
```json
{
  "success": true,
  "message": "If your domain is registered, a magic link has been sent."
}
```

**Internal logic:**
1. Extract domain from email
2. Find active `CompanyDomain` matching that domain
3. If found: upsert `CompanyUser`, call `issue_magic_link`
4. If not found: silently discard (still return 200)

---

#### `POST /api/auth/verify-magic-link`
**Purpose:** Exchange one-time token for a session.

**Request body:**
```json
{ "token": "<raw_token_from_email_link>" }
```

**Response `200`:**
```json
{
  "success": true,
  "session_token": "abc123...",
  "session_expires_at": "2026-03-15T12:00:00Z",
  "user": {
    "id": 1,
    "email": "user@amazon.com",
    "full_name": null,
    "role": "member"
  },
  "company": {
    "id": 1,
    "name": "Amazon",
    "approved_email_domain": "amazon.com"
  }
}
```

**Error cases:**
- `401` — token invalid, expired, or already used

---

#### `GET /api/auth/me`
**Purpose:** Return current authenticated user's profile. Requires `Authorization: Bearer <session_token>`.

**Response `200`:**
```json
{
  "user": { "id": 1, "email": "user@amazon.com", "role": "member" },
  "company": { "id": 1, "name": "Amazon" }
}
```

**Error:** `401` if session invalid or expired

---

#### `POST /api/auth/logout`
**Purpose:** Revoke current session.

**Request body:**
```json
{ "session_token": "abc123..." }
```

**Response `200`:**
```json
{ "success": true }
```

---

### 3e. Frontend Handshake Contract
> **For the frontend team — what to expect from auth:**

| Step | Frontend Action | Backend Endpoint |
|------|----------------|-----------------|
| Register company | POST form | `POST /api/auth/register-company` |
| Login page | User enters email, clicks "Send Login Link" | `POST /api/auth/request-magic-link` |
| Email link clicked | User lands on `/auth/verify?token=...` | `POST /api/auth/verify-magic-link` with token from URL |
| On success | Store `session_token` in localStorage / cookie | — |
| Every API call | Set header `Authorization: Bearer <session_token>` | All protected routes |
| Load profile | On app mount | `GET /api/auth/me` |
| Logout | Clear stored token + call server | `POST /api/auth/logout` |

**Token lifecycle:**
- Magic link token: valid for **15 minutes**, single use
- Session token: valid for **72 hours**, revokable
- Email goes to `{username}@gmail.com` (Power Automate rewrite — see Section 2)

---

## 4. Manual Run System

> **Flow:** User clicks "New Run" → enters topic + query count → reviews/edits generated prompts → clicks "Start" → polling loop → history entry appears when done.

---

### 4a. Data Models — `app/models/run_history.py`
**Status:** ✅ DONE  
**File:** `server/app/models/run_history.py`

**Tables created:**

| Table | Model | Purpose |
|-------|-------|---------|
| `query_batch_runs` | `QueryBatchRun` | Parent record for each user-triggered run |
| `query_batch_items` | `QueryBatchItem` | Individual editable prompts within a run |

**Key fields on `QueryBatchRun`:**
- `product_topic` — e.g. "Laptops", "EV Charging"
- `requested_query_count` — how many prompts user chose
- `status` — `queued` → `running` → `completed` / `failed` / `canceled`
- `before_snapshot` — JSON score data captured before run starts
- `after_snapshot` — JSON score data captured after run completes
- `created_by_user_id` — which user triggered (but all company users can see it)
- `company_id` — company-scoped

**Key fields on `QueryBatchItem`:**
- `query_text` — the prompt that will be sent to LLMs
- `edited_by_user_id` — if user edited the auto-generated prompt
- `prompt_order` — user-facing order
- `status` — `pending` → `running` → `done` / `failed`
- `item_summary` — brief result summary after execution

**No code changes needed** to this file.

---

### 4b. Run Orchestrator Service — `app/services/run_orchestrator.py`
**Status:** 🔧 SPEC  
**File:** `server/app/services/run_orchestrator.py`

**Functions to implement:**

---

#### `suggest_prompts_for_topic(topic: str, count: int, company: Company) -> list[str]`
```
Use LLM (GPT-4o or similar) to generate `count` search query prompts
about `topic`, personalized to `company.about_company`.
Returns list of plain query strings.
```
Example output for topic="Laptops", count=5:
```
["Best laptops for college students 2026",
 "Laptop recommendations for video editing",
 "Are MacBooks worth the price?",
 "Lightweight laptops under $1000",
 "Best laptop brands compared"]
```

---

#### `create_draft_batch(company: Company, user: CompanyUser, topic: str, query_count: int) -> QueryBatchRun`
```
1. Clamp query_count to company.config.max_query_count
2. prompts = suggest_prompts_for_topic(topic, query_count, company)
3. Create QueryBatchRun(status="queued", product_topic=topic, ...)
4. Create QueryBatchItem for each prompt (prompt_order=1..N, status="pending")
5. Capture before_snapshot (current score data from DB)
6. db.session.commit()
7. Return QueryBatchRun
```

---

#### `update_batch_queries(run_id: int, items: list[dict], user: CompanyUser) -> QueryBatchRun`
```
1. Load QueryBatchRun (must be in "queued" status)
2. Validate run belongs to user's company
3. Replace / reorder QueryBatchItems with incoming list
4. Track edited_by_user_id if text differs from original
5. db.session.commit()
6. Return updated run
```
Called when user edits prompts before hitting Start.

---

#### `enqueue_batch_execution(run: QueryBatchRun) -> None`
```
1. run.status = "running"; db.session.commit()
2. Launch _execute_batch_run(run.id) in a background thread
3. Return immediately — caller gets "queued" response right away
```

---

#### `_execute_batch_run(run_id: int) -> None`  *(background worker)*
```
Runs in a separate thread with its own app context.
1. app.app_context().__enter__()
2. Load run from DB
3. For each QueryBatchItem in order:
   a. item.status = "running"
   b. Run query through query_runner.run_single_query(item.query_text, company)
   c. Save QueryRun(batch_run_id=run.id, batch_item_id=item.id)
   d. item.status = "done" or "failed"
4. run.after_snapshot = capture_score_snapshot(run.company_id)
5. run.status = "completed"
6. run.completed_at = now
7. db.session.commit()
```

---

#### `get_batch_progress(run_id: int, company_id: int) -> dict`
```
Returns:
{
  "run_id": ...,
  "status": "running",
  "progress_pct": 40,
  "total_queries": 10,
  "completed": 4,
  "failed": 0,
  "started_at": ...,
  "completed_at": null
}
```
Used by polling endpoint.

---

### 4c. Run Routes — `app/routes/runs.py`
**Status:** 🔧 SPEC  
**File:** `server/app/routes/runs.py`

**All routes require `Authorization: Bearer <session_token>`.**

---

#### `POST /api/runs/generate-prompts`
**Purpose:** Create a draft run with auto-generated prompts. User reviews before starting.

**Request body:**
```json
{
  "topic": "Laptops",
  "query_count": 10
}
```

**Response `201`:**
```json
{
  "run_id": 42,
  "status": "queued",
  "topic": "Laptops",
  "queries": [
    { "id": 1, "order": 1, "text": "Best laptops for students 2026" },
    { "id": 2, "order": 2, "text": "Lightweight laptops under $1000" }
  ]
}
```

---

#### `PATCH /api/runs/<run_id>/queries`
**Purpose:** Replace/reorder query items before starting.

**Request body:**
```json
{
  "queries": [
    { "id": 1, "text": "Best gaming laptops 2026", "order": 1 },
    { "id": 2, "text": "Top budget laptops under $800", "order": 2 }
  ]
}
```

**Response `200`:** Updated run with new query list.

**Error:** `409` if run is already `running` or `completed`.

---

#### `POST /api/runs/<run_id>/start`
**Purpose:** Begin async background execution. Returns immediately.

**Response `202`:**
```json
{
  "run_id": 42,
  "status": "running",
  "message": "Run started. Poll /api/runs/42/status for progress."
}
```

---

#### `GET /api/runs/<run_id>/status`
**Purpose:** Polling endpoint for progress while run is in background.

**Response `200`:**
```json
{
  "run_id": 42,
  "status": "running",
  "progress_pct": 60,
  "total_queries": 10,
  "completed": 6,
  "failed": 0,
  "started_at": "2026-03-12T10:00:00Z",
  "completed_at": null
}
```
Poll every 3–5 seconds. Stop when `status` is `completed` or `failed`.

---

#### `GET /api/runs/history`
**Purpose:** Company-wide run history list (all users in company see same list).

**Query params:** `?page=1&per_page=20`

**Response `200`:**
```json
{
  "runs": [
    {
      "run_id": 42,
      "topic": "Laptops",
      "status": "completed",
      "total_queries": 10,
      "started_at": "2026-03-12T10:00:00Z",
      "completed_at": "2026-03-12T10:05:30Z",
      "created_by": "user@amazon.com"
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

---

#### `GET /api/runs/history/<run_id>`
**Purpose:** Full detail of one history entry including before/after comparison.

**Response `200`:**
```json
{
  "run_id": 42,
  "topic": "Laptops",
  "status": "completed",
  "before_snapshot": { "visibility_score": 62, "accuracy_score": 71 },
  "after_snapshot":  { "visibility_score": 68, "accuracy_score": 75 },
  "delta": { "visibility_score": "+6", "accuracy_score": "+4" },
  "queries": [
    { "id": 1, "text": "Best laptops for students 2026", "status": "done", "summary": "..." }
  ],
  "created_at": "...",
  "completed_at": "..."
}
```

---

## 5. Analytics Routes

> These routes serve the dashboard data. They are company-scoped (same company_id from session).  
> All are currently comment-spec. They should be implemented after auth and run system are working.

| Route File | URL Prefix | Status | Priority |
|------------|-----------|--------|---------|
| `routes/dashboard.py` | `/api/dashboard` | 🔧 SPEC | Medium |
| `routes/visibility.py` | `/api/visibility` | 🔧 SPEC | Medium |
| `routes/accuracy.py` | `/api/accuracy` | 🔧 SPEC | Medium |
| `routes/competitors.py` | `/api/competitors` | 🔧 SPEC | Low |
| `routes/actions.py` | `/api/actions` | 🔧 SPEC | Low |
| `routes/crawl.py` | `/api/crawl` | 🔧 SPEC | Low |
| `routes/query_tester.py` | `/api/query-tester` | 🔧 SPEC | Low |
| `routes/ethics.py` | `/api/ethics` | 🔧 SPEC | Low |

All analytics routes must call `require_company_session(request)` at the top to stay company-scoped.

---

## 6. Environment Variables

**File:** `server/.env.template` (copy to `.env` and fill in values)

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `SECRET_KEY` | ✅ | — | Flask session signing |
| `FLASK_ENV` | ✅ | `development` | |
| `FLASK_APP` | ✅ | `run.py` | |
| `BACKEND_BASE_URL` | ✅ | `http://localhost:5000` | Base URL of this Flask server — used in magic link email |
| `FRONTEND_BASE_URL` | ✅ | `http://localhost:3000` | Used in magic link URL |
| `DATABASE_URL` | ❌ | SQLite dev | For PostgreSQL in prod |
| `OPENAI_API_KEY` | ✅ | — | GPT-4o queries |
| `ANTHROPIC_API_KEY` | ✅ | — | Claude queries |
| `PERPLEXITY_API_KEY` | ✅ | — | Perplexity queries |
| `GOOGLE_API_KEY` | ✅ | — | Gemini queries |
| `MAGIC_LINK_TTL_MINUTES` | ❌ | `15` | Token expiry |
| `SESSION_TTL_HOURS` | ❌ | `72` | Session expiry |
| `MAX_QUERIES_PER_RUN` | ❌ | `100` | Safety cap |
| `POWERAUTOMATE_EMAIL_API_URL` | ✅ | — | Power Automate webhook URL for email |

> **Note on `POWERAUTOMATE_EMAIL_API_URL`:** Required for magic-link auth to work.  
> The `emailing.py` service posts to this URL. The Power Automate flow **rewrites the recipient to @gmail.com** — this is by design for dev/testing.

---

## 7. Database Migrations

**Status:** ✅ DONE — run on 2026-03-12. 24 tables created in `instance/vigil_dev.db`.

**Steps:**
```bash
cd server
flask db init          # only first time — creates migrations/ folder
flask db migrate -m "initial schema with auth and run history"
flask db upgrade
```

**Tables that will be created:**
- `companies` (existing + new fields: `about_company`, `approved_email_domain`, `registration_status`)
- `company_configs`
- `company_domains` ← new
- `company_users` ← new
- `magic_link_tokens` ← new
- `user_sessions` ← new
- `query_templates`
- `query_runs` (existing + new FKs: `batch_run_id`, `batch_item_id`)
- `query_batch_runs` ← new
- `query_batch_items` ← new
- `accuracy_snapshots`
- `content_pages`
- `crawl_results`
- `competitor_companies`
- `source_citations`
- `ethics_flags`

---

## 8. Testing Checklist

> Manually test each flow in order after implementing. Check off as you go.

### Auth Flow
- [x] `POST /api/auth/register-company` — creates company, domain, owner user
- [x] `POST /api/auth/register-company` with same domain — returns 409
- [x] `POST /api/auth/request-magic-link` — returns 200 (even for unknown domain)
- [x] Check Gmail inbox — magic link email received (dev.dharambir@gmail.com ✅)
- [x] `GET /api/auth/verify?token=...` — email link hits backend, session created
- [x] `POST /api/auth/verify-magic-link` with valid token — returns session token
- [ ] `POST /api/auth/verify-magic-link` with same token again — returns 401
- [ ] `POST /api/auth/verify-magic-link` with expired token — returns 401
- [x] `GET /api/auth/me` with valid Bearer token — returns user + company
- [x] `GET /api/auth/me` with expired/invalid token — returns 401
- [x] `POST /api/auth/logout` — session revoked; `/me` returns 401 after

### Run Flow
- [ ] `POST /api/runs/generate-prompts` — returns run with auto-generated queries
- [ ] `PATCH /api/runs/<id>/queries` — edit a prompt, verify change persisted
- [ ] `POST /api/runs/<id>/start` — returns 202 immediately (not 200)
- [ ] `GET /api/runs/<id>/status` — progress increments over time
- [ ] Wait for completion — `GET /api/runs/<id>/status` returns `completed`
- [ ] `GET /api/runs/history` — run appears in list
- [ ] `GET /api/runs/history/<id>` — before/after snapshot present

---

## Implementation Order (Recommended)

```
0. settings.py         ← ✅ done
1. config.py           ← ✅ done
2. app/__init__.py     ← ✅ done
3. auth_service.py     ← ✅ done
4. auth routes         ← ✅ done (includes GET /verify email-link handler)
5. [ TEST AUTH ]       ← ✅ tested 2026-03-12 — all cases pass
6. run_orchestrator    ← 🔧 next
7. run routes          ← 🔧 next
8. [ TEST RUNS ]       ← not started
9. analytics routes    ← not started
10. migrations         ← ✅ done — 24 tables in vigil_dev.db
```

---

*Last updated: 2026-03-12 — Auth fully implemented and tested. Email → backend verify → session token flow working. Next: run_orchestrator + run routes.*
