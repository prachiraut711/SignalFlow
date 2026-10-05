# SignalFlow Documentation

Welcome to the documentation for **SignalFlow — Business Event Intelligence & Anomaly Detection Platform**.

## Architecture Overview (Planned)

SignalFlow is engineered to ingest, process, and analyze business application events in near-real-time to detect operational anomalies.

```
[ Client / Business Apps ]
           │
           ▼
[ FastAPI Ingestion API ]
           │ (Push to Stream)
           ▼
    [ Redis Streams ]
           │
    ┌──────┴──────────────┐
    ▼                     ▼
[ Stream Worker ]     [ Anomaly Detector ]
    │                     │
    ▼                     ▼
[ PostgreSQL / DuckDB ] [ Alerts / Notifications ]
           ▲
           │
[ React + Vite Dashboard ]
```

## System Components
1. **Frontend**: Modern React + TypeScript + Tailwind CSS analytics dashboard.
2. **Backend**: FastAPI REST API providing event ingestion endpoints, analytics querying, and health monitoring.
3. **Stream Buffer**: Redis Streams for high-throughput decoupled event buffering.
4. **Data Storage**:
   - **PostgreSQL**: Transactional storage for metadata, rules, configurations, and aggregated events.
   - **DuckDB**: Fast in-process columnar analytical query engine for temporal event aggregations.
5. **Detection Engine**: Statistical & machine learning anomaly detection routines.
