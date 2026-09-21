# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Aura is an AI-powered Instagram compliment generator. It scrapes Instagram posts, analyzes images with Google Gemini (or Llama.cpp), and generates styled compliments. The system uses an event-driven architecture with Redis Streams for background task processing and WebSockets for real-time client updates.

## Architecture

- **Backend:** FastAPI (async Python), PostgreSQL 15 (SQLModel ORM), Redis 7 (Streams), Alembic migrations
- **Frontend:** React 19 + TypeScript, Vite 6, Chakra UI 2, React Router 7, Axios
- **Workers:** Two Redis Stream consumers — `instagram_download_worker` (scrapes posts) and `llm_worker` (generates compliments)
- **Auth:** JWT (HS256) + OAuth2PasswordBearer, bcrypt passwords, email verification

### Data Flow

1. User submits Instagram URL → API creates Task + Post → pushes to Redis stream `tasks:instagram_download:stream`
2. Instagram worker consumes task, downloads images, publishes status to `task:{id}:updates` stream
3. User requests compliment → API creates LLM task → pushes to `tasks:compliment_generation:stream`
4. LLM worker consumes task, calls Gemini API with image, stores Compliment + GenerationMetadata
5. WebSocket endpoint `/ws/{task_id}` streams Redis updates to the client

### Backend Layers

- `api/routes/` — HTTP endpoints (controllers)
- `service/` — business logic
- `data/` — CRUD / data access layer
- `models/` — SQLModel ORM models
- `schemas/` — Pydantic request/response DTOs
- `workers/` — Redis Stream consumers (run as separate processes)
- `core/config/` — Pydantic v2 settings composed in `settings.py`
- `api/deps.py` — FastAPI dependency injection (`CurrentUser`, `AsyncSessionDep`, services)

## Common Commands

### Backend

```bash
# Start all services (DB, Redis, API, workers, mailcrab)
cd backend && docker compose up --build

# Run only migrations (tools profile)
cd backend && docker compose run --rm migrate

# Linting & formatting
cd backend && bash scripts/lint.sh    # ruff check + mypy
cd backend && bash scripts/format.sh  # ruff format

# Tests
cd backend && bash scripts/test.sh    # pytest with coverage

# Alembic migrations
cd backend && alembic upgrade head
cd backend && alembic revision --autogenerate -m "description"
```

### Frontend

```bash
cd frontend && npm install
cd frontend && npm run dev        # Vite dev server
cd frontend && npm run build      # Production build
cd frontend && npx eslint .       # Lint
```

## Code Style

### Backend
- **Ruff** for linting (import sorting rule "I") and formatting (double quotes, 2-space indent)
- **MyPy** for type checking (strict mode)
- Full async stack — use `async/await` throughout

### Frontend
- **ESLint** with strict TypeScript + React rules, 120 char line limit
- Import sorting via `eslint-plugin-import`
- Context-based state management (User, Post, Task contexts in `src/contexts/`)

## Docker Services

postgres (5432), redis (6379), app (8000), instagram_worker, llm_worker, mailcrab (1080/1025)

## Key Environment Variables

See `backend/.env.example`. Notable: `LLM_PROVIDER` (GEMINI|LLAMA), `INSTAGRAM_SCRAPER` (INSTALOADER|PLAYWRIGHT), `ENVIRONMENT` (local|production).
