# VIGIL Frontend Architecture

Frontend is organized to mirror backend modules so future API expansion stays clean and predictable.

## Structure

```text
client/
├── src/
│   ├── app/
│   │   ├── App.jsx
│   │   ├── AppRouter.jsx
│   │   └── paths.js
│   ├── components/
│   │   ├── common/
│   │   │   ├── AuthCard.jsx
│   │   │   └── FeaturePlaceholder.jsx
│   │   └── layout/
│   │       ├── DashboardLayout.jsx
│   │       └── ProtectedRoute.jsx
│   ├── features/
│   │   ├── auth/pages/
│   │   │   ├── LoginPage.jsx
│   │   │   ├── RegisterPage.jsx
│   │   │   └── VerifyPage.jsx
│   │   ├── dashboard/pages/DashboardOverviewPage.jsx
│   │   ├── runs/pages/RunsPage.jsx
│   │   ├── visibility/pages/VisibilityPage.jsx
│   │   ├── accuracy/pages/AccuracyPage.jsx
│   │   ├── competitors/pages/CompetitorsPage.jsx
│   │   ├── actions/pages/ActionsPage.jsx
│   │   ├── crawl/pages/CrawlPage.jsx
│   │   ├── ethics/pages/EthicsPage.jsx
│   │   └── query-tester/pages/QueryTesterPage.jsx
│   ├── pages/
│   │   └── HomePage.jsx
│   ├── services/
│   │   ├── apiClient.js
│   │   ├── authApi.js
│   │   └── session.js
│   ├── styles/
│   │   └── app.css
│   ├── index.css
│   └── main.jsx
└── README.md
```

## Routing Map

- `/` → Home (entry buttons to register/login)
- `/register` → Company registration
- `/login` → Magic-link request
- `/auth/verify` → Frontend token verification fallback

Protected workspace routes:
- `/dashboard`
- `/runs`
- `/visibility`
- `/accuracy`
- `/competitors`
- `/actions`
- `/crawl`
- `/ethics`
- `/query-tester`

## Backend Mapping

### Auth APIs
- `POST /api/auth/register-company`
- `POST /api/auth/request-magic-link`
- `POST /api/auth/verify-magic-link`
- `GET /api/auth/me`
- `POST /api/auth/logout`

### Feature APIs (scaffolded pages ready)
- `/api/dashboard/*`
- `/api/runs/*`
- `/api/visibility/*`
- `/api/accuracy/*`
- `/api/competitors/*`
- `/api/actions/*`
- `/api/crawl/*`
- `/api/ethics/*`
- `/api/query-tester/*`

## Session Flow

1. User lands from backend verify redirect: `/dashboard?session_token=...`
2. `ProtectedRoute` stores token and allows entry.
3. `DashboardLayout` loads `/api/auth/me` for company context.
4. Sidebar navigation is available for all modules.
5. Logout revokes backend session and clears local token.

## How to Add New API Module

1. Create page in `src/features/<module>/pages/`.
2. Add route constant in `src/app/paths.js`.
3. Add sidebar nav entry in `DASHBOARD_NAV_ITEMS`.
4. Register route in `src/app/AppRouter.jsx`.
5. Add service methods in `src/services/`.

## Development

```bash
npm install
npm run dev
```

Optional env:

```bash
VITE_API_BASE_URL=http://localhost:5000
```
