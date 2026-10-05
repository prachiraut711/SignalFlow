"""
Simulation Scenarios Specification and Metadata
"""

from typing import Any, Dict, List, Optional
from app.schemas.simulator import SimulationScenario


SUPPORTED_REGIONS = ["Pune", "Mumbai", "Delhi", "Bangalore", "Hyderabad"]
SUPPORTED_SERVICES = [
    "payment-service",
    "order-service",
    "auth-service",
    "inventory-service",
    "notification-service",
]

SCENARIO_METADATA: Dict[SimulationScenario, Dict[str, Any]] = {
    SimulationScenario.NORMAL_TRAFFIC: {
        "title": "Normal Traffic",
        "description": "Healthy baseline application traffic with nominal latency and minimal error rate (< 2%).",
        "default_service": "payment-service",
        "default_region": "Pune",
        "expected_anomaly": None,
    },
    SimulationScenario.PAYMENT_FAILURE_SPIKE: {
        "title": "Payment Failure Spike",
        "description": "Normal payment operations followed by an abrupt surge in payment failures (25-30%) and high latency (2-3s).",
        "default_service": "payment-service",
        "default_region": "Pune",
        "expected_anomaly": "Payment Service Degradation (Error Rate + Latency Spike)",
    },
    SimulationScenario.API_ERROR_SPIKE: {
        "title": "API Error Spike",
        "description": "Standard API operations followed by elevated HTTP 500/502/503 server errors on the order service.",
        "default_service": "order-service",
        "default_region": "Pune",
        "expected_anomaly": "Order Service Error Spike",
    },
    SimulationScenario.HIGH_LATENCY: {
        "title": "High Latency Degradation",
        "description": "Successful operations (HTTP 200) that degrade significantly into extreme response times (2-4 seconds).",
        "default_service": "order-service",
        "default_region": "Pune",
        "expected_anomaly": "Order Service Latency Degradation",
    },
    SimulationScenario.TRAFFIC_SURGE: {
        "title": "Traffic Surge",
        "description": "Sudden volume surge (3x-4x traffic) with healthy response status codes, demonstrating volume detection.",
        "default_service": "order-service",
        "default_region": "Pune",
        "expected_anomaly": "Order Service Traffic Anomaly",
    },
    SimulationScenario.REGIONAL_FAILURE: {
        "title": "Regional Failure (Pune Outage)",
        "description": "Multi-region traffic where Pune datacenter suffers elevated errors and latency while other regions remain healthy.",
        "default_service": "payment-service",
        "default_region": "Pune",
        "expected_anomaly": "Pune Regional Service Degradation",
    },
}
