# SignalFlow — Business Event Intelligence & Anomaly Detection Platform

> A resilient, observable event intelligence platform engineered to ingest high-volume business telemetry, detect operational anomalies in real time, and deliver diagnostic insights for distributed architectures.

---

## 1. Project Overview

**SignalFlow** is a modern, medium-level distributed event intelligence platform. It provides end-to-end observability into critical business operations (e.g., checkout flows, payment processing, user registration, inventory updates) by streaming telemetry events through a fast decoupled pipeline, applying statistical and machine learning anomaly detection routines, and presenting actionable metrics on an analytics dashboard.

---

## 2. Problem Being Solved

In modern microservice and service-oriented architectures, failures often manifest not as infrastructure crashes (e.g., high CPU), but as subtle **business process breakdowns**:
* A 40% sudden drop in completed orders following a third-party payment gateway update.
* A silent surge in failed checkout events due to an expired authorization token.
* Latency spikes across multi-step business transactions.

Standard infrastructure monitoring (e.g., server CPU, memory, disk) often fails to catch these domain-level regressions promptly. **SignalFlow** bridges this gap by:
1. Ingesting standardized business event telemetry at high throughput.
2. Buffering events reliably to handle traffic surges without dropping payloads.
3. Automatically identifying anomalies using sliding-window statistical baselines and ML models.
4. Enabling fast ad-hoc analytical queries on aggregated business events.
5. Providing root-cause diagnostic context to accelerate incident remediation.

---

## 3. Technology Stack

### Current (Phase 1 — Foundation)
* **Frontend**: React 18, TypeScript, Vite, React Router, Tailwind CSS, Lucide Icons
* **Backend**: Python 3.12, FastAPI, Pydantic v2, Uvicorn
* **DevOps & Containerization**: Docker, Docker Compose
* **Testing & Quality**: Pytest, HTTPX

### Planned (Upcoming Phases)
* **Stream Buffer**: Redis Streams (decoupled ingestion buffer, consumer groups)
* **Primary Relational Store**: PostgreSQL (audit records, metadata, rules, alert history via SQLAlchemy)
* **Columnar Analytical Engine**: DuckDB (sub-second local aggregations and time-series rollups)
* **Anomaly Detection Engine**: Scikit-Learn (Isolation Forests) + Statistical sliding-window Z-Score / IQR
* **Root-Cause Intelligence**: Google Gemini API (automated failure summarization and diagnostics)
* **CI/CD**: GitHub Actions (linting, type-checking, automated unit and integration tests)

---

## 4. Architecture

### System Architecture Diagram (Planned)

```
┌────────────────────────────────┐
│   Client Applications / Apps   │
└───────────────┬────────────────┘
                │ HTTP POST /events (Batch & Single)
                ▼
┌────────────────────────────────┐
│      FastAPI Ingestion API     │
└───────────────┬────────────────┘
                │ XADD (Fast Append)
                ▼
┌────────────────────────────────┐
│          Redis Streams         │
└───────┬────────────────┬───────┘
        │                │
        │ Consumer Group │ Consumer Group
        ▼                ▼
┌─────────────────┐    ┌──────────────────────────────────┐
│  Stream Worker  │    │  Anomaly Detection Worker        │
│  (Persistence)  │    │  (Z-Score / Isolation Forest)    │
└───────┬─────────┘    └────────────────┬─────────────────┘
        │                               │
        ▼                               ▼
┌─────────────────┐           ┌───────────────────┐
│ PostgreSQL /    │           │ Alerts & Root     │
│ DuckDB Analytics│◄──────────┤ Cause Diagnostics │
└───────▲─────────┘           │ (Gemini API)      │
        │                     └───────────────────┘
        │ REST API Queries
┌───────┴─────────────────┐
│ React + Vite Dashboard  │
└─────────────────────────┘
```

---

## 5. Current Development Status

| Component | Status | Details |
| :--- | :--- | :--- |
| **Project Foundation** | **Completed** | Clean full-stack folder structure, configuration, environment templates, and Docker Compose |
| **Backend Core** | **Completed** | FastAPI service initialized, configuration loading via Pydantic, `GET /health` and `GET /health/redis` operational |
| **Event Ingestion API** | **Completed** | Validated ingestion endpoint (`POST /api/events`) with server-side unique ID generation |
| **Redis Stream Pipeline** | **Completed** | Buffering validated events in real-time to `signalflow:events` with XADD |
| **Stream Consumers** | **Completed** | Resilient `EventWorker` daemon consuming consumer groups with XREADGROUP and XACK |
| **DuckDB Analytics Store** | **Completed** | Embedded analytical event table with batch insertion and transactional querying |
| **Analytics APIs** | **Completed** | Aggregation endpoints for `/api/analytics/overview`, `/api/analytics/services`, and 1-minute `/windows` |
| **Database Connectors** | **Completed** | PostgreSQL relational storage via SQLAlchemy with automatic local SQLite fallback for dev |
| **Anomaly Detection** | **Completed** | Dual-layer detection: Statistical (Z-score + % change) & ML (Isolation Forest) with deduplication |
| **Signal Correlation** | **Completed** | Correlates related anomalies into incident signals (`OPEN`/`RESOLVED`) with 10-min windowing |
| **AI Incident Explanation** | **Completed** | OpenRouter LLM diagnostic summaries, hypotheses, and recommended remediation steps |
| **Frontend SaaS Dashboard** | **Completed** | React + TypeScript + Vite + Tailwind + Recharts monitoring dashboard with incident triage & AI insights |
| **Event Simulator** | **Completed** | Realistic multi-scenario event simulation engine sending live telemetry through `POST /api/events` |


---

## 6. Directory Structure

```text
SignalFlow/
├── frontend/                 # React + TypeScript + Vite SaaS client
│   ├── src/
│   │   ├── components/      # UI components (Header, Sidebar, Badges, Charts, StatCard, etc.)
│   │   ├── pages/           # Pages (Dashboard, Signals, SignalDetail, Events, Services, Simulator)
│   │   ├── lib/             # API client & TypeScript interfaces (api.ts)
│   │   ├── App.tsx          # Router layout & navigation configuration
│   │   ├── main.tsx         # React root entrypoint
│   │   ├── index.css        # Tailwind CSS imports & styling
│   │   └── vite-env.d.ts    # Vite environment type definitions
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── Dockerfile
├── backend/                  # FastAPI Python backend application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application & lifespan management
│   │   ├── config.py        # Pydantic Settings configuration (Redis, PG, OpenRouter)
│   │   ├── api/             # API routes (health, events, analytics, anomalies, signals, ai, simulator)
│   │   ├── db/              # Database connectors (PostgreSQL/SQLite, Redis, DuckDB)
│   │   ├── models/          # SQLAlchemy models (AnomalyRecord, SignalRecord, SignalAnomaly)
│   │   ├── schemas/         # Pydantic validation schemas (Events, Anomalies, Signals, AI, Simulator)
│   │   ├── services/        # Business logic (Event, Analytics, Anomaly, Signal, AI Explanation)
│   │   ├── workers/         # Background stream consumers (EventWorker)
│   │   ├── ml/              # Statistical & Isolation Forest anomaly detectors
│   │   └── simulator/       # Event Simulator (scenarios, generator, service)
│   ├── tests/               # Pytest suite (65 unit & functional tests)
│   ├── requirements.txt
│   ├── .env.example         # Backend environment variables template
│   └── Dockerfile
├── docs/                     # Architecture & specifications
│   └── architecture.md
├── tests/                    # End-to-end integration tests (Planned)
├── docker-compose.yml        # Development environment services
├── .gitignore
├── .env.example              # Environment variables template
└── README.md
```

---

## 7. Local Setup Instructions

### Prerequisites
* **Node.js**: v18+ (v22 recommended)
* **Python**: 3.11+ (3.12 recommended)
* **Git**
* *(Optional)* **Docker & Docker Compose**

---

### Option A: Local Native Setup (Recommended for Step 1)

#### 1. Backend Setup

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   * **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   * **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. Verify backend health:
   * Open: `http://localhost:8000/health`
   * Interactive API docs: `http://localhost:8000/docs`

---

#### 2. Frontend Setup

1. Open a second terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

4. Open the starter application in your browser:
   * URL: `http://localhost:5173`
   * The page will automatically query the backend `/health` endpoint and display its status.

---

### Option B: Docker Compose Setup

To start all baseline containers (Backend, Frontend, PostgreSQL, Redis):

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Start the services:
   ```bash
   docker compose up --build
   ```

3. Access the services:
   * Frontend: `http://localhost:5173`
   * Backend API: `http://localhost:8000`
   * API Documentation: `http://localhost:8000/docs`
   * PostgreSQL: `localhost:5432`
   * Redis: `localhost:6379`

---

## 8. Anomaly Detection Pipeline (Phase 4)

SignalFlow incorporates a **dual-layer anomaly detection architecture** designed for high precision, low latency, and clear diagnostic explainability:

### 1. Statistical Detector (`app/ml/statistical_detector.py`)
- **Rolling Baseline Windows**: Evaluates 1-minute time windows against a dynamic historical baseline (up to 30 prior consecutive minutes).
- **Z-Score & Percentage Change**: Computes standard deviation, Z-score, and relative percent deviations for `error_rate`, `average_latency_ms`, and `event_count`.
- **Deterministic Severity Tiers**:
  - `CRITICAL`: Error rate $\ge 15\%$ with $+200\%$ spike or $Z \ge 3.5$; latency $\ge 1800\text{ms}$ with $+200\%$ spike.
  - `HIGH`: $Z \ge 2.5$ or percentage deviation $\ge 150\%$.
  - `WARNING`: $Z \ge 2.0$ or percentage deviation $\ge 75\%$.
  - `INFO`: Mild baseline fluctuation ($Z \ge 1.5$).
- **Zero-Variance Resilience**: Safely handles static metrics without division-by-zero or math errors.

### 2. Machine Learning Detector (`app/ml/anomaly_detector.py`)
- **Isolation Forest**: Fits `scikit-learn` `IsolationForest` across multidimensional feature vectors:
  $$[\text{event\_count}, \text{error\_rate}, \text{average\_latency\_ms}]$$
- Detects non-linear, multivariate outliers where individual metrics may appear borderline but composite behavior is abnormal.

### 3. Anomaly Orchestrator & Persistence (`app/services/anomaly_service.py`)
- **Relational Storage**: Persists anomalies to PostgreSQL (or SQLite local fallback) with database-enforced unique constraints:
  `UniqueConstraint("service", "time_window", "metric")`
- **Deduplication**: Prevents alert fatigue by ensuring repeated detection triggers do not create duplicate records.
- **REST Endpoints**:
  - `GET /api/anomalies`: Query detected anomalies with filters (`service`, `severity`, `limit`).
  - `POST /api/anomalies/detect`: Trigger an evaluation run across all services.

---

## 9. Signal Correlation & Incidents (Phase 5)

Anomalies represent individual abnormal metrics (e.g., error rate spike or latency degradation). **Signals** group multiple related anomalies into a single, cohesive operational incident using service, region, and sliding time-proximity windows.

```text
error_rate spike (CRITICAL)
          +
latency spike (CRITICAL)
          ↓
Payment Service Degradation (CRITICAL, OPEN)
```

- **Correlation Rules**: Clusters unlinked anomalies sharing the same `service`, `region`, and detected within a dynamic **10-minute** window.
- **Deterministic Incident Titling**:
  - `error_rate` only $\rightarrow$ `Payment Service Error Spike`
  - `average_latency_ms` only $\rightarrow$ `Payment Service Latency Degradation`
  - `error_rate` + `average_latency_ms` $\rightarrow$ `Payment Service Degradation`
  - `event_count` $\rightarrow$ `Payment Service Traffic Anomaly`
- **Severity Aggregation**: Highest priority among attached anomalies (`CRITICAL` > `HIGH` > `WARNING` > `INFO`).
- **Incident Lifecycle**: Supports transition from `OPEN` to `RESOLVED` while preserving full historical anomaly audit trails.
- **REST Endpoints**:
  - `GET /api/signals`: Query signals with filtering (`severity`, `status`, `service`, `region`, `limit`).
  - `GET /api/signals/{id}`: Detailed signal representation with all attached raw anomalies.
  - `POST /api/signals/correlate`: Trigger manual anomaly correlation scan.
  - `POST /api/signals/{id}/resolve`: Resolve an operational incident.

---

## 10. AI Incident Explanation (Phase 6)

SignalFlow integrates **OpenRouter** (OpenAI-compatible HTTP chat completions) to transform structured incident telemetry into concise, human-readable operational diagnostics.

```text
Signal
  ↓
Structured incident context
  ↓
OpenRouter LLM (e.g. openrouter/free)
  ↓
Summary + Likely Causes + Recommended Actions
```

> [!NOTE]
> The LLM functions strictly as an **explanation layer**. It does not perform anomaly detection, signal correlation, database queries, or autonomous operations. Detection and correlation remain 100% deterministic within SignalFlow's statistical and ML engines.

- **Non-blocking Configuration**: Runs gracefully with or without `OPENROUTER_API_KEY`. If unconfigured, the endpoint returns a clean `503 Service Unavailable` error without crashing.
- **Controlled Prompting**: Distinguishes verified observations from possible hypotheses (hypotheses are never stated as confirmed facts).
- **REST Endpoint**:
  - `POST /api/signals/{signal_id}/explain`: Generates fresh on-demand operational guidance for an incident signal.

---

## 11. Frontend SaaS Dashboard (Phase 7)

SignalFlow features a responsive, dark-first SaaS monitoring dashboard built with **React 18**, **TypeScript**, **Vite**, **Tailwind CSS**, and **Recharts**. The frontend connects directly to the FastAPI backend with live telemetry and automatic polling:

### Views & Capabilities:
1. **Overview Dashboard (`/`)**:
   - Executive telemetry stat cards (Total Events, Error Rate, Average Latency, Active Incidents, Total Anomalies, Correlated Signals).
   - Real-time **Event Throughput AreaChart** with gradient fill.
   - Stacked **Success vs. Error Count BarChart**.
   - **Service Health Matrix** classifying service tiers (Healthy $\le 3\%$, Degraded $3-10\%$, Critical $> 10\%$).
   - Quick-action table of high-priority operational signals.

2. **Incident Signals (`/signals`)**:
   - Filterable signals list by Severity (`INFO`, `WARNING`, `HIGH`, `CRITICAL`), Status (`OPEN`, `RESOLVED`), Service, and Region.
   - On-demand **Trigger Correlation Scan** button to group recent anomalies into operational signals.

3. **Signal Investigation Detail (`/signals/:id`)**:
   - Correlated anomaly inspection with individual baseline comparisons, percentage changes, Z-scores, and diagnostic reasons.
   - On-demand **AI Incident Explanation** powered by OpenRouter (summary, likely root causes, recommended action checklist).
   - Incident lifecycle actions (Mark as `RESOLVED`).

4. **Event Explorer (`/events`)**:
   - Raw analytical event stream loaded directly from DuckDB with server-side filtering (`service`, `event_type`, `region`, `status_code`) and pagination.

5. **Service Directory (`/services`)**:
   - Per-service health cards displaying total events, error counts, failure rate, and mean response latency.

6. **Event Simulator (`/simulator`)**:
   - Dedicated interactive control console for launching and managing realistic event simulation scenarios.

---

## 12. Event Simulator (Phase 8)

SignalFlow features a realistic **Event Simulation Engine** that models distributed system behaviors and failure modes. Crucially, the simulator does not inject synthetic records directly into the databases or frontend state; it dispatches valid application events through the real production ingestion route:

```text
Event Simulator
      ↓
POST /api/events
      ↓
FastAPI Ingestion
      ↓
Redis Stream (signalflow:events)
      ↓
Processing Worker (EventWorker)
      ↓
DuckDB Analytical Store
      ↓
Dual-Layer Anomaly Detection
      ↓
Signal Correlation
      ↓
SaaS Dashboard
```

### Supported Failure Scenarios:
1. **Normal Traffic**: Baseline healthy application traffic across all services with low error rate ($< 2\%$) and nominal response latency ($120-420\text{ms}$).
2. **Payment Failure Spike**: Healthy baseline transitioning into an abrupt surge in transaction failures ($30\%$ error rate) and high latency ($2-3\text{s}$) on `payment-service`.
3. **API Error Spike**: Sudden elevated HTTP 500/502/503 server errors on `order-service` ($35\%$ failure rate).
4. **High Latency Degradation**: Successful operations (predominantly HTTP 200) that degrade significantly into extreme response times ($2-4\text{s}$).
5. **Traffic Surge**: Sudden throughput volume spike ($3\text{x}-4\text{x}$ traffic) while preserving low error rates, exercising volume anomaly detection.
6. **Regional Failure (Pune Outage)**: Multi-region traffic where the Pune datacenter suffers elevated errors and latency while other geographic regions remain healthy.

### Example Incident Progression:
```text
Payment Failure Spike
        ↓
payment_failed events increase
        ↓
error rate increases
        ↓
latency increases
        ↓
anomaly detected (Statistical + Isolation Forest)
        ↓
signal created ("Payment Service Degradation")
        ↓
AI explanation available (OpenRouter LLM)
```

### Safe Simulation Limits:
- **Events per second**: $1$ to $50\text{ eps}$ (rejects values outside this range).
- **Duration**: $5$ to $300\text{ seconds}$ (rejects values outside this range).
- **Execution Concurrency**: Singleton enforcement (only one active simulation allowed at a time).

---

## 13. Running Tests & Verification

### Backend Tests
From the `backend` directory (with active virtual environment):
```bash
pytest -v
```

### Frontend Type-Check & Build
From the `frontend` directory:
```bash
npm run build
```

---

## 14. Design Philosophy

* **Medium Complexity & Interview-Focused**: Architected with enterprise best practices (type-safety, modular structure, asynchronous I/O, clean separation of concerns) without unnecessary complexity or tool sprawl (no Kafka/Kubernetes/Spark where lightweight alternatives like Redis Streams and DuckDB excel).
* **Independent Execution**: Frontend and Backend are decoupled and can run or be tested entirely independently.
* **Observability-First**: Built from day one with system health tracking and structured telemetry schemas.


