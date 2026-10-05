"""
Statistical Anomaly Detection Module

Detects metric deviations using rolling baselines, Z-scores, and percentage changes
with deterministic, interview-explainable thresholding and severity scoring.
"""

import math
from typing import Any, Dict, List, Optional, Tuple


def calculate_mean_and_std(values: List[float]) -> Tuple[float, float]:
    """Calculate sample mean and standard deviation for a series of numbers."""
    if not values:
        return 0.0, 0.0
    n = len(values)
    mean = sum(values) / n
    if n < 2:
        return mean, 0.0
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    return mean, math.sqrt(variance)


def calculate_z_score(current: float, mean: float, std: float) -> Optional[float]:
    """
    Compute standard score: z = (x - mean) / std.
    Returns 0.0 if standard deviation is zero and current matches mean.
    Returns None if standard deviation is zero but current deviates (handled via % change).
    """
    if math.isclose(std, 0.0, abs_tol=1e-6):
        return 0.0 if math.isclose(current, mean, abs_tol=1e-6) else None
    return round((current - mean) / std, 2)


def detect_percentage_change(current: float, baseline: float) -> float:
    """
    Calculate relative percentage change: ((current - baseline) / baseline) * 100.
    Handles zero baseline cases safely.
    """
    if baseline <= 1e-6:
        if current <= 1e-6:
            return 0.0
        return 100.0  # Shift from zero to positive represents 100%+ increase
    return round(((current - baseline) / baseline) * 100.0, 2)


def determine_severity(
    metric: str,
    current: float,
    baseline: float,
    z_score: Optional[float],
    pct_change: float,
) -> Tuple[str, str]:
    """
    Determine anomaly severity (INFO, WARNING, HIGH, CRITICAL) and generate
    deterministic diagnostic explanation based on deviation magnitude.

    Threshold Logic:
    - CRITICAL: Extreme degradation (Z >= 4.0 OR Error Rate > 15% with +200% spike, OR Latency +300%)
    - HIGH:     Significant degradation (Z >= 3.0 OR Pct Change >= 150%)
    - WARNING:  Moderate deviation (Z >= 2.0 OR Pct Change >= 75%)
    - INFO:     Mild deviation (Z >= 1.5)
    """
    z_abs = abs(z_score) if z_score is not None else 0.0

    if metric == "error_rate":
        if (z_score is not None and z_score >= 3.5) or (current >= 15.0 and pct_change >= 200.0):
            return "CRITICAL", f"Critical error surge: error rate is {current}% (+{pct_change}% over {baseline}% baseline)"
        elif (z_score is not None and z_score >= 2.5) or (current >= 8.0 and pct_change >= 100.0):
            return "HIGH", f"High error spike: error rate is {current}% (+{pct_change}% over {baseline}% baseline)"
        elif z_abs >= 2.0 or pct_change >= 75.0:
            return "WARNING", f"Elevated errors: error rate reached {current}% (+{pct_change}% over baseline)"
        else:
            return "INFO", f"Minor error rate variance: {current}% compared to {baseline}%"

    elif metric == "average_latency_ms":
        if (z_score is not None and z_score >= 3.5) or (current >= 1800.0 and pct_change >= 200.0):
            return "CRITICAL", f"Severe latency degradation: {current:.1f}ms (+{pct_change}% over {baseline:.1f}ms baseline)"
        elif (z_score is not None and z_score >= 2.5) or pct_change >= 150.0:
            return "HIGH", f"High latency spike: {current:.1f}ms (+{pct_change}% over {baseline:.1f}ms baseline)"
        elif z_abs >= 2.0 or pct_change >= 75.0:
            return "WARNING", f"Elevated latency: {current:.1f}ms (+{pct_change}% over baseline)"
        else:
            return "INFO", f"Minor latency fluctuation: {current:.1f}ms compared to {baseline:.1f}ms"

    else:  # event_count or default
        if z_abs >= 3.5 or abs(pct_change) >= 200.0:
            return "HIGH", f"Major traffic volume shift: {current:.0f} events ({pct_change:+.1f}% change)"
        elif z_abs >= 2.0 or abs(pct_change) >= 100.0:
            return "WARNING", f"Moderate volume shift: {current:.0f} events ({pct_change:+.1f}% change)"
        else:
            return "INFO", f"Minor traffic variation: {current:.0f} events"


def detect_statistical_anomaly(
    metric: str,
    current_value: float,
    baseline_values: List[float],
) -> Optional[Dict[str, Any]]:
    """
    Evaluate whether current metric value is anomalous relative to baseline history.

    Args:
        metric: Metric name ('error_rate', 'average_latency_ms', 'event_count')
        current_value: Metric value in current evaluation window
        baseline_values: Historic metric values from prior consecutive windows

    Returns:
        Dictionary with anomaly metadata if anomalous, None otherwise.
    """
    if not baseline_values:
        return None

    baseline_mean, baseline_std = calculate_mean_and_std(baseline_values)
    z_score = calculate_z_score(current_value, baseline_mean, baseline_std)
    pct_change = detect_percentage_change(current_value, baseline_mean)

    is_anomaly = False
    anomaly_type = f"{metric}_deviation"

    # Evaluation conditions
    if metric == "error_rate":
        # Anomaly if z >= 2.0 OR significant absolute & relative percentage jump
        if (z_score is not None and z_score >= 2.0) or (current_value >= 8.0 and pct_change >= 75.0):
            is_anomaly = True
            anomaly_type = "error_rate_spike"
    elif metric == "average_latency_ms":
        # Anomaly if z >= 2.0 OR latency doubled (>100% change) with at least 500ms
        if (z_score is not None and z_score >= 2.0) or (current_value >= 600.0 and pct_change >= 100.0):
            is_anomaly = True
            anomaly_type = "latency_spike"
    elif metric == "event_count":
        if (z_score is not None and abs(z_score) >= 2.5) or abs(pct_change) >= 150.0:
            is_anomaly = True
            anomaly_type = "traffic_surge" if pct_change > 0 else "traffic_drop"

    if not is_anomaly:
        return None

    severity, reason = determine_severity(
        metric=metric,
        current=current_value,
        baseline=baseline_mean,
        z_score=z_score,
        pct_change=pct_change,
    )

    return {
        "is_anomaly": True,
        "anomaly_type": anomaly_type,
        "metric": metric,
        "current_value": round(current_value, 2),
        "baseline_value": round(baseline_mean, 2),
        "percentage_change": pct_change,
        "z_score": z_score,
        "severity": severity,
        "reason": reason,
    }
