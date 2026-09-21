# Aura — event-driven media-analysis backend

An async, event-driven backend that ingests a social-media post URL, fetches its images, runs them through a multimodal LLM, and streams a short styled text with a structured tone breakdown back to the client in real time.

Built solo, by hand (summer 2025). Deployed live on AWS, later shelved when the upstream platform blocked datacenter-IP scraping. Backend only — the claimable substance is the architecture, not a product.

## Architecture

- **FastAPI producer** — creates a Task, publishes to a Redis Stream, returns immediately
- **Two dedicated workers** (download + LLM) consuming via consumer groups (`XGROUP`/`XREADGROUP`/`XACK`), concurrency capped with `asyncio.Semaphore`
- **Idempotency** — pre-work DB check emits a `skipped` status when the image already exists
- **Live status streaming** — workers publish progress to a per-task stream (`task:{id}:updates`); an authenticated, ownership-checked WebSocket tails it with `XREAD`, terminating on `done`/`failed`/`skipped`
- **Data model** — eight SQLModel tables over PostgreSQL 15 with Alembic migrations; per-invocation LLM telemetry (model, token counts, latency) in its own table; tone breakdown as JSONB
- **LLM integration** — Gemini multimodal with `response_mime_type="application/json"`, parsed into a Pydantic schema, `tenacity` exponential-backoff retries
- **Ops** — Docker Compose (postgres, redis, api, two workers, SMTP sink); GitHub Actions SSH-deploy to EC2 with a post-deploy health check