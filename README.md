# Hissabi Accounting Platform

Modern SMB accounting stack combining a FastAPI backend, Next.js front-end, and optional background workers. This repository now mirrors the production surface exposed to clients.

## Repository Layout
- `backend/api` – FastAPI service powering authentication, document ingestion, inventory, analytics, and Stripe webhooks.
- `web-app` – Next.js 15 client with React Query + local mocks for rapid UI iteration.
- `backend/analytics-worker` – Celery worker stub (see folder README) for future async processing.
- `backend/api-gateway` – Placeholder for edge gateway logic (documented in its README).
- `mobile-app` – React Native skeleton (documented in its README).
- `infra/terraform` – DigitalOcean infrastructure definitions.
- `docker-compose.yml` – Local dev stack (API + Postgres + Redis).

## Backend Highlights
- JWT auth with per-organisation tenancy and plan-aware feature gating.
- Document uploads (CSV/XLSX) with robust table cleaning and LLM-assisted inventory mapping.
- Inventory summaries, movement history, accounting statement generation, and analytics P&L endpoint.
- Stripe webhook ingestion and paywall enforcement via `require_plan`.

## Frontend Highlights
- App router layout with protected routes, app shell, and MSW-powered mocks.
- React Query + token-aware API client aligned with backend responses.
- Dashboard sections for uploads, documents, inventory, and analytics.

## Getting Started
```bash
cd backend/api
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cd ../../web-app
pnpm install
```

Use `docker-compose up --build` to launch the full stack locally. Enable MSW in the web app for mock data (`NEXT_PUBLIC_USE_MSW=1`).
