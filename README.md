# GSU_TECH_03132026

This project contains a Vite React client and a Flask backend.

## One-command local run (Docker)

1. Create a root `.env` file (you can copy from `server/.env.template`).
2. Start the full app:

```bash
docker compose up --build
```

App URLs:
- Client: http://localhost:5173
- API: http://localhost:5000

Stop:

```bash
docker compose down
```

## Deploy to Render

This repo now includes a Render Blueprint file: `render.yaml`.

### Quick deploy

1. Push this repo to GitHub.
2. In Render, choose **New +** → **Blueprint**.
3. Select this repository.
4. Render creates:
   - `vigil-api` (Python web service)
   - `vigil-client` (static site)

### Environment variables to set in Render

For `vigil-api`:
- `SECRET_KEY` (required)
- `DATABASE_URL` (required for production DB)
- `FRONTEND_BASE_URL` (set to your `vigil-client` URL)
- `BACKEND_BASE_URL` (set to your `vigil-api` URL)
- API keys used by your app (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, etc.)

For `vigil-client`:
- `VITE_API_BASE_URL` should point to your API public URL

## Notes

- Render does not run `docker-compose.yml` directly in production; use `render.yaml` for deployment orchestration.
- Local development remains one command with Docker Compose.
