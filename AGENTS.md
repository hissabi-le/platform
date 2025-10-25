# Repository Guidelines

## Project Structure & Module Organization
- `backend/api`: FastAPI service; core logic in `src/`, tests in `tests/`, migrations scaffold under `alembic/`.
- `web-app`: Next.js 15 client; pages/components in `src/`, mocks in `src/mocks/`, configs at repo root.
- `backend/analytics-worker`, `backend/api-gateway`, `mobile-app`: documented stubs—add implementation-specific code under each folder’s `src/` when activating.
- `infra/terraform`: DigitalOcean provisioning templates; run terraform commands from this directory.

## Build, Test, and Development Commands
- `docker-compose up --build`: Launch API, Postgres, Redis, and worker locally.
- `cd backend/api && python3 -m pytest`: Execute backend test suite.
- `cd backend/api && uvicorn src.main:app --reload`: Run FastAPI server without Docker.
- `cd web-app && pnpm install && pnpm dev`: Install dependencies and start the Next.js dev server (MSW mocks auto-start unless `NEXT_PUBLIC_USE_MSW=0`).

## Coding Style & Naming Conventions
- Python: Pydantic v2 + Ruff defaults (line length 88); follow async SQLAlchemy patterns already in `src/`.
- TypeScript/React: adhere to Next.js app router conventions; components in PascalCase; hooks start with `use`.
- Keep new env vars UPPER_SNAKE_CASE and document them in README or `.env.example`.

## Testing Guidelines
- Backend uses `pytest`; name tests `test_*.py` and colocate fixtures under `tests/`.
- Frontend relies on React Testing Library/MSW (not yet wired); prefer component-level tests in `web-app/src/__tests__/`.
- Verify analytics/inventory flows with representative sample data before merging.

## Commit & Pull Request Guidelines
- Use imperative commit subjects (e.g., `Add inventory movement endpoint`); group related changes per commit.
- Pull requests should include a brief summary, testing evidence (`python3 -m pytest`, `pnpm lint`), and mention any new env/config requirements.
- Attach screenshots or terminal output for UI changes; cross-link Linear/Jira tickets when available.

## Security & Configuration Tips
- Never commit secrets; rely on `.env` files ignored by Git and DigitalOcean secrets in Terraform.
- Rotate API keys used by `OpenAIClient` and Stripe; validate webhook signatures with `STRIPE_WEBHOOK_SECRET`.
- Ensure `JWT_SECRET` and database credentials are set in production before deploying.
