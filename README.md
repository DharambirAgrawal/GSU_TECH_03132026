# GSU_TECH_03132026

This repository has two apps:
- `client` (frontend)
- `server` (Flask backend)

## Run Everything with Docker

### 1) Create root `.env`

Create `.env` in this root folder.

Use `server/.env.template` as the reference for required server variables.

### 2) Start client + server

```bash
docker compose up --build
```

### 3) Access services

- Client: http://localhost:5173
- Server: http://localhost:5000

## Useful Docker Commands

Stop and remove containers:

```bash
docker compose down
```

View logs:

```bash
docker compose logs -f
```
