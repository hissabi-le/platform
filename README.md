# Hisabi Accounting Platform

A full-stack, AI-powered accounting system designed for small and medium businesses (SMBs). The platform automates financial document ingestion, generates professional accounting statements and financial reports, and provides real-time analytics through an intelligent, multi-tenant architecture.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                    │
│                         Next.js 15 (App Router)                         │
│              React Query | TypeScript | Tailwind CSS                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              Backend API                                 │
│                    FastAPI (Python 3.12, Async)                         │
│         SQLAlchemy 2.0 | Pydantic V2 | JWT Auth | Dramatiq             │
└─────────────────────────────────────────────────────────────────────────┘
         │                          │                          │
         ▼                          ▼                          ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐
│   PostgreSQL    │    │      Redis      │    │   OpenAI API (GPT-4o)   │
│  (Primary DB)   │    │  (Cache/Queue)  │    │   Document Intelligence │
└─────────────────┘    └─────────────────┘    └─────────────────────────┘
```

---

## Key Technical Features

### Intelligent Database Design

The PostgreSQL schema is designed for multi-tenant SaaS operations with organization-level isolation:

- **Multi-Tenant Architecture**: All entities are scoped to `org_id` with cascading foreign keys, ensuring strict data isolation between customer organizations.
- **Normalized Transaction Model**: Financial transactions are stored with full audit trails, including source upload references, entry types (revenue, cost, inventory), and parsed metadata.
- **Inventory Tracking**: Weighted-average cost (WAC) inventory system with movement history, supporting FIFO/LIFO reporting extensions.
- **Journal System**: Free-text and structured journal entries with AI-assisted parsing, clarification workflows, and resolution tracking.
- **Optimized Indexing**: Strategic composite indexes on `(org_id, date)`, `(org_id, item_id, timestamp)` for efficient time-series queries and multi-tenant access patterns.

### AI-Powered Document Processing

The ingestion pipeline leverages GPT-4o for intelligent document understanding:

1. **File Parsing**: Accepts CSV, XLSX, and PDF uploads with automatic format detection.
2. **Table Cleaning**: Robust header detection, merged cell handling, and data normalization.
3. **LLM Extraction**: Structured prompts extract transactions, categorize accounts (Chart of Accounts aligned), and detect AR/AP entries.
4. **Clarification Workflow**: Ambiguous entries are flagged for user resolution before final commit.

### Backend Architecture

- **FastAPI with Async SQLAlchemy**: Fully asynchronous request handling with connection pooling.
- **Repository Pattern**: Clean separation between business logic and data access.
- **Plan-Aware Feature Gating**: `require_plan()` decorators enforce subscription-based access to premium features.
- **Stripe Integration**: Webhook handlers for subscription lifecycle management and paywall enforcement.
- **Background Processing**: Dramatiq workers for long-running document processing tasks.
- **Caching Layer**: Redis-backed analytics cache with TTL-based invalidation.

### Frontend Architecture

- **Next.js 15 App Router**: Server and client components with optimized rendering.
- **React Query**: Data fetching with intelligent caching, background refetching, and optimistic updates.
- **Type-Safe API Client**: Auto-generated TypeScript types aligned with Pydantic models.
- **Dark Mode**: System-aware theme switching via `next-themes`.
- **MSW Integration**: Mock Service Worker for offline-first development and testing.

---

## Repository Structure

```
platform/
├── backend/
│   └── api/                    # FastAPI application
│       ├── src/
│       │   ├── routers/        # API route handlers
│       │   ├── repositories/   # Data access layer
│       │   ├── tasks/          # Background job definitions
│       │   ├── models.py       # SQLAlchemy ORM models
│       │   ├── database.py     # Async DB session management
│       │   ├── security.py     # JWT auth and plan enforcement
│       │   └── balance_sheet.py # Financial statement generation
│       └── pyproject.toml      # Python dependencies
├── web-app/                    # Next.js frontend
│   ├── src/
│   │   ├── app/                # App Router pages
│   │   ├── components/         # Reusable UI components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── lib/                # API client and utilities
│   │   └── mocks/              # MSW handlers for development
│   └── package.json
├── infra/
│   └── terraform/              # Infrastructure as Code (DigitalOcean)
├── docker-compose.yml          # Local development stack
└── docker-compose.prod.yml     # Production configuration
```

---

## Technology Stack

| Layer          | Technology                                                  |
|----------------|-------------------------------------------------------------|
| Frontend       | Next.js 15, React 19, TypeScript, Tailwind CSS, React Query |
| Backend        | FastAPI, Python 3.12, SQLAlchemy 2.0, Pydantic V2           |
| Database       | PostgreSQL 16 (async via asyncpg)                           |
| Cache/Queue    | Redis 7, Dramatiq                                           |
| AI/ML          | OpenAI GPT-4o (document parsing and extraction)             |
| Auth           | JWT (access + refresh tokens), bcrypt                       |
| Payments       | Stripe subscriptions and webhooks                           |
| Infrastructure | Docker, Railway (PaaS), DigitalOcean (IaC via Terraform)    |
| Testing        | Pytest (backend), Vitest (frontend), MSW (API mocking)      |

---

## Local Development

### Prerequisites

- Python 3.12+
- Node.js 20+ with pnpm
- Docker and Docker Compose
- PostgreSQL 16+ (or use Docker)
- Redis 7+ (or use Docker)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/hissabi-le/platform.git
cd platform

# Start infrastructure services
docker-compose up -d postgres redis

# Backend setup
cd backend/api
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn src.main:app --reload

# Frontend setup (new terminal)
cd web-app
pnpm install
pnpm dev
```

### Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/hisabi
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=your-secret-key
OPENAI_API_KEY=sk-...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

---

## API Highlights

| Endpoint                      | Description                                    |
|-------------------------------|------------------------------------------------|
| `POST /auth/login`            | JWT authentication                             |
| `POST /uploads`               | File upload with async processing              |
| `GET /documents`              | List generated financial documents             |
| `POST /journal`               | Submit journal entries (free-text or structured)|
| `GET /analytics/pnl`          | Profit and Loss with configurable date ranges  |
| `GET /inventory/summary`      | Current inventory levels with WAC              |
| `POST /analytics/generate`    | Generate Balance Sheet, P&L, or Cash Flow      |

---

## Deployment

The platform is deployed on Railway with the following services:

- **API**: FastAPI backend with Gunicorn/Uvicorn workers
- **Worker**: Dramatiq background processor for document ingestion
- **Web**: Next.js frontend with static optimization
- **Database**: Managed PostgreSQL
- **Cache**: Managed Redis

Infrastructure can also be provisioned via Terraform to DigitalOcean.

---

## License

Proprietary. All rights reserved.

---

## Contact

For technical inquiries or collaboration opportunities, please reach out via the repository issues or email.
