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
| **Backend Core** | **Completed** | FastAPI service initialized, configuration loading via Pydantic, `GET /health` operational |
| **Frontend Starter** | **Completed** | React + TypeScript + Vite + Tailwind CSS SaaS starter layout with backend health monitoring |
| **Database Connectors** | *Planned* | PostgreSQL, Redis Streams, and DuckDB connection lifecycles prepared in Phase 1 |
| **Event Ingestion API** | *Planned* | Validated endpoints for ingestion (`POST /events`) |
| **Redis Stream Pipeline** | *Planned* | Ingestion buffer and consumer group workers |
| **Anomaly Detection** | *Planned* | Sliding-window Z-score & ML anomaly classification |
| **Analytical Dashboard** | *Planned* | Real-time charts, event tables, and metric breakdowns |
| **Gemini Diagnostics** | *Planned* | LLM-driven root-cause incident summaries |
| **Event Simulator** | *Planned* | Realistic event generation script with injectable anomalies |

---

## 6. Directory Structure

```text
SignalFlow/
├── frontend/                 # React + TypeScript + Vite web client
│   ├── src/
│   │   ├── App.tsx          # Starter page with health status & architecture
│   │   ├── main.tsx         # React root entrypoint
│   │   └── index.css        # Tailwind styling
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── Dockerfile
├── backend/                  # FastAPI Python backend application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application & /health route
│   │   ├── config.py        # Pydantic Settings configuration
│   │   ├── api/             # API route controllers
│   │   ├── db/              # Database connection placeholders (PG, Redis, DuckDB)
│   │   ├── models/          # Data / ORM models (Planned)
│   │   ├── schemas/         # Pydantic schemas (Request/Response)
│   │   ├── services/        # Business logic services (Planned)
│   │   ├── workers/         # Background stream workers (Planned)
│   │   └── ml/              # Anomaly detection models (Planned)
│   ├── tests/               # Backend pytest suite
│   ├── requirements.txt
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

## 8. Running Tests

### Backend Tests
From the `backend` directory (with active virtual environment):
```bash
pytest -v
```

---

## 9. Design Philosophy

* **Medium Complexity & Interview-Focused**: Architected with enterprise best practices (type-safety, modular structure, asynchronous I/O, clean separation of concerns) without unnecessary complexity or tool sprawl (no Kafka/Kubernetes/Spark where lightweight alternatives like Redis Streams and DuckDB excel).
* **Independent Execution**: Frontend and Backend are decoupled and can run or be tested entirely independently.
* **Observability-First**: Built from day one with system health tracking and structured telemetry schemas.
