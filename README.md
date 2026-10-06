# SignalFlow

SignalFlow is a business event intelligence and anomaly detection platform that ingests application events, detects unusual behavior, correlates related anomalies into incidents, and provides AI-assisted operational explanations.

![Platform Overview](docs/screenshots/platform%20overview.png)

## Problem

Modern applications generate large volumes of telemetry events (payments, API requests, errors, latency, user activity). Manually identifying abnormal behavior across this stream is difficult and error-prone.

SignalFlow helps answer:
* "What is happening?"
* "Which service/region is affected?"
* "How severe is it?"
* "Are multiple anomalies related?"

## How It Works

```text
Event Simulator / External App
        ↓
POST /api/events
        ↓
Redis Streams
        ↓
Background Worker
        ↓
DuckDB + PostgreSQL
        ↓
Statistical + Isolation Forest Detection
        ↓
Signal Correlation
        ↓
OpenRouter AI Explanation
        ↓
React Dashboard
```

* **Event Ingestion**: Telemetry is ingested via `POST /api/events` and buffered into Redis Streams. The simulator sends events through this real API and does not directly fake dashboard metrics.
* **Stream Processing**: A background worker consumes stream batches with consumer groups and stores events in DuckDB.
* **Analytical Rollups**: DuckDB aggregates 1-minute time windows, while PostgreSQL/SQLite stores persistent anomalies and signals.
* **Detection & Correlation**: Statistical rules and Isolation Forest detect regressions, which are correlated into incidents within a 10-minute window.
* **AI & Presentation**: OpenRouter provides operational incident explanations surfaced on a React dashboard.

## Key Features

- Real-time event ingestion
- Redis Streams processing
- DuckDB analytics
- PostgreSQL persistence
- Statistical anomaly detection
- Isolation Forest detection
- Multi-anomaly incident correlation
- Incident severity and resolution
- OpenRouter AI diagnostics
- Event Explorer
- Service Explorer
- Event Simulator
- Docker Compose
- GitHub Actions CI

## Screenshots

### Platform Overview
![Platform Overview](docs/screenshots/platform%20overview.png)
*Executive dashboard showing platform event volume, error rate, latency, and top open incidents.*

### Event Simulator
![Event Simulator](docs/screenshots/event%20simulator.png)
*Generates realistic application telemetry across 6 failure scenarios through the real ingestion API.*

### Incident Analysis
![Incident Analysis](docs/screenshots/incident%20analysis.png)
*Incident detail view correlating co-occurring anomalies across error rate and latency.*

### AI Operational Diagnostics
![AI Operational Diagnostics](docs/screenshots/Ai%20operational%20Diagnostics.png)
*Contextual operational explanations, hypotheses, and remediation checklists powered by OpenRouter.*

### Event Explorer
![Event Explorer](docs/screenshots/event%20explorer%20screen.png)
*Searchable raw event explorer displaying underlying telemetry records stored in DuckDB.*

### Service Explorer
![Service Explorer](docs/screenshots/service%20explore%20screen.png)
*Comparative microservice view displaying health badges, error rates, and average latencies.*

## Anomaly Detection

Statistical detection:
- rolling baseline
- z-score
- percentage change
- threshold rules

Isolation Forest:
- event count
- error rate
- average latency

Detection and severity are determined by backend logic; AI is used only to explain detected incidents.

## AI Diagnostics

OpenRouter analyzes detected incident telemetry to produce:
- incident summary
- likely hypotheses
- recommended investigation/remediation steps

AI outputs are hypotheses, not confirmed root causes.

Configured via `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, and `OPENROUTER_BASE_URL` in `.env`. The application works fully without an AI key.

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React, TypeScript, Vite, Tailwind, shadcn/ui, Recharts |
| **Backend** | Python, FastAPI, Pydantic, SQLAlchemy |
| **Data** | PostgreSQL, DuckDB, Pandas, NumPy |
| **Streaming** | Redis Streams |
| **ML** | scikit-learn Isolation Forest + statistical detection |
| **AI** | OpenRouter |
| **DevOps** | Docker, Docker Compose, GitHub Actions |
| **Testing** | Pytest |

## Quick Start

**Requirements**: Docker Desktop, Git

```bash
git clone https://github.com/prachiraut711/SignalFlow.git
cd SignalFlow

# Copy environment template (add OpenRouter variables if AI diagnostics are desired)
cp .env.example .env

# Start all services
docker compose up -d
```

* **Frontend**: http://localhost:5173
* **Backend API**: http://localhost:8000
* **Swagger Docs**: http://localhost:8000/docs
* **Stop**: `docker compose down`

## Demo

1. Open **Simulator**.
2. Select **Payment Failure Spike**.
3. Select `payment-service` and `Pune`.
4. Click **Start Simulation**.
5. Click **Run Pipeline Scan**.
6. Open **Signals**.
7. Inspect **Payment Service Degradation**.
8. Click **Generate AI Analysis**.
9. Inspect **Events** and **Services**.

**Expected result**: error rate spike, latency spike, traffic surge, correlated CRITICAL incident, and an AI operational explanation.

## Testing & CI

- 70 backend tests passing
- Frontend production build passing
- End-to-end smoke test passing
- GitHub Actions CI configured

```bash
python -m pytest backend/tests -q
cd frontend && npm run build
python tests/smoke_test.py
```

## Deployment

SignalFlow is pre-configured for free cloud hosting (Render + Neon + Upstash):

- **Backend**: Render Web Service (`EMBED_WORKER=true` runs stream processing in-process; dynamic `$PORT` binding).
- **Frontend**: Render Static Site (`frontend/dist`, SPA client rewrites via `public/_redirects`).
- **PostgreSQL**: Neon serverless Postgres (`DATABASE_URL=postgresql://...`).
- **Redis Streams**: Upstash Redis with TLS (`REDIS_URL=rediss://...`).
- **Blueprint**: Use `render.yaml` or deploy manually. Connect services using `FRONTEND_URL` and `VITE_API_BASE_URL`.

## Project Status

Status: Complete for portfolio/demo use.

Core pipeline: Event ingestion → processing → analytics → anomaly detection → incident correlation → AI diagnostics → dashboard.
