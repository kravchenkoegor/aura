# Production-ready improvement plan

## Critical improvements

### P0: Architectural blockers (MUST FIX before production deployment)

#### 1. Stateful architecture

**Current state:**
- `instagram_download_worker` saves files to local container filesystem
- `proxy.py` streams files from local disk through FastAPI backend
- Images tied to specific worker containers

**Problems:**
- **Cannot horizontally scale**: User requests image on Replica A, but file stored on Replica B's disk
- **Ephemeral storage**: Kubernetes/ECS pod restart => all images lost
- **Backend bandwidth bottleneck**: 5MB image download blocks async worker, consumes RAM/CPU
- **Single point of failure**: Worker dies => images inaccessible

**Solution:**
- Integrate Object Storage (S3/GCS/MinIO)
- Worker streams downloads directly to S3, stores S3 key in DB
- API generates presigned URLs for direct client→S3 downloads
- Remove `proxy.py` entirely

#### 2. Instagram scraper will likely fail immediately in the cloud

**Current state:**
- `instaloader` called directly from workers
- No proxy rotation, no anti-bot measures

**Problems:**
- Instagram aggressively blocks datacenter IPs (AWS/GCP/Azure)
- Rate limits will block the entire service
- One worker IP ban => all tasks fail

**Solutions:**
- Integrate rotating proxy service (Bright Data, ZenRows, ScraperAPI)
- Or: separate scraping into dedicated microservice with residential proxies
- Or: use official Instagram Graph API (requires business verification)
- Add circuit breaker to prevent cascading failures

---

### P1: Critical security & operational issues

#### 3. Sentry configured but never initialized

**Problem:**
- Sentry SDK dependency installed and DSN configured, but `sentry_sdk.init()` never called, resulting in zero error tracking in production.

**Solution:**
- Initialize Sentry in `app/main.py` with environment check to enable error tracking for non-local environments.

#### 4. Database exposed on port 5432

**Problem:**
- PostgreSQL exposed on public port 5432 in docker-compose creates unnecessary attack surface and violates least privilege principle.

**Solution:**
- Create separate docker-compose files (dev with ports, prod without) or remove port mapping to keep database accessible only via internal Docker network.

#### 5. Database migrations run on every container startup

**Current state:**
- `prestart.sh` runs `alembic upgrade head`
- Multiple containers starting simultaneously
- Migration failures block app startup

**Problem:**
- Multiple replicas starting simultaneously cause race conditions; migration failures prevent all containers from starting.

**Solution:**
- Remove migrations from `prestart.sh` and run as separate deployment job/script before container rollout.

---

### P1: Observability

#### 6. Structured logging with JSON output

**Current state:**
- Text-based logging
- No correlation IDs
- Cannot query logs at scale

**Problem:**
- Text logs cannot be efficiently parsed/queried in log aggregation systems (ELK, Datadog), making production debugging difficult.

**Solution:**
- Replace standard logging with `structlog` configured for JSON output to enable machine-readable logs.

#### 7. Request correlation IDs

**Problem:**
- No request tracing across services makes it impossible to follow a single request through the distributed system for debugging.

**Solution:**
- Add correlation ID middleware that injects unique IDs into request context and propagates them through all logs and external calls.

---

### P2: Reliability improvements

#### 8. Retry logic for downloading images from Instagram

**Problem:**
- Instagram download calls fail permanently on transient network errors, requiring manual user retry and degrading UX.

**Solution:**
- Wrap `instaloader` calls with exponential backoff retry mechanism (3 attempts) to handle temporary network failures automatically.

#### 9. Circuit Breaker Pattern

**Problem:**
- Slow or failing external services cascade through system, blocking workers and causing queue backlog.

**Solution:**
- Implement circuit breaker on external API calls to fast-fail when service is degraded, preventing cascading failures.

#### 10. Dead Letter Queue Implementation

**Problem:**
- Failed tasks are logged and lost forever with no recovery mechanism; poison messages can block queue indefinitely.

**Solution:**
- Move tasks that fail after 3 retry attempts to separate Redis DLQ stream for manual inspection and replay capability.

---

### Database improvements

#### 11. Add missing indexes

**Problem:**
- Foreign keys like `Image.post_id`, `Post.author_id`, `Compliment.image_id` lack indexes, causing slow joins and table scans as data grows.

**Solution:**
- Add `index=True` to all foreign key fields and create Alembic migration to optimize query performance.

#### 12. Redis persistence configuration

**Problem:**
- Redis runs without persistence configuration, causing all queue data and task state to be lost on container restart.

**Solution:**
- Enable Redis AOF (Append-Only File) persistence with `--appendonly yes --appendfsync everysec` to survive restarts.

---

### Infrastructure & Deployment

#### 13. Multi-Worker setup with Gunicorn

**Problem:**
- Single Uvicorn process cannot utilize multiple CPU cores and has no process management or auto-restart capability.

**Solution:**
- Replace with Gunicorn using 4 Uvicorn workers for production-grade process management and resource utilization.

#### 14. Resource limits

**Problem:**
- Docker services have no CPU/memory limits, allowing one service to starve others of resources (noisy neighbor problem).

**Solution:**
- Add resource limits and reservations to docker-compose for each service to ensure predictable performance and prevent resource exhaustion.

#### 15. Health check & readiness endpoints

**Problem:**
- Missing `/health` and `/ready` endpoints prevent load balancers and orchestrators from determining service health, causing failed deployments.

**Solution:**
- Add health endpoint (simple 200 OK) and readiness endpoint (checks Redis/DB connectivity) for proper orchestration support.

#### 16. Graceful shutdown

**Problem:**
- In-flight requests are abruptly terminated during deployments, causing poor user experience and potential data inconsistency.

**Solution:**
- Implement SIGTERM signal handlers to drain connections and allow current requests to complete before shutdown.

---

### API Design improvements

#### 17. API versioning

**Problem:**
- Routes lack version prefix (e.g., `/tasks/` instead of `/v1/tasks/`), preventing safe evolution of API with breaking changes.

**Solution:**
- Add `/api/v1` prefix to all routes to enable future non-breaking changes and proper API lifecycle management.

#### 18. Proper pagination response

**Problem:**
- List endpoints return raw arrays without metadata (total count, page info), preventing efficient pagination and poor UX.

**Solution:**
- Return standardized pagination object with `items`, `total`, `page`, `size`, and `pages` fields for all list endpoints.

---

### Testing strategy

#### 19. Comprehensive unit tests

**Problem:**
- Only one test file exists covering <5% of codebase, leaving business logic untested and vulnerable to regressions.

**Solution:**
- Write unit tests for service layer with proper mocking (aim for 60%+ coverage) and add to CI pipeline.

#### 20. Integration or E2E Tests

**Problem:**
- No end-to-end testing means component integration bugs only discovered in production, not during development.

**Solution:**
- Write integration tests covering critical user flows (task creation → processing → completion) with test fixtures and real database.