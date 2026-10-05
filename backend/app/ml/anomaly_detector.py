"""
Isolation Forest Machine Learning Anomaly Detector

Uses scikit-learn's Isolation Forest algorithm to detect multi-dimensional outliers
across aggregated time-window telemetry features:
[event_count, error_rate, average_latency_ms].
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class IsolationForestDetector:
    """
    Unsupervised outlier detector for aggregated service telemetry.
    """

    def __init__(
        self,
        contamination: float = 0.05,
        n_estimators: int = 100,
        random_state: int = 42,
    ):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.model: Optional[IsolationForest] = None

    @staticmethod
    def extract_features(window_dict: Dict[str, Any]) -> List[float]:
        """
        Extract numerical feature vector: [event_count, error_rate, average_latency_ms].
        """
        return [
            float(window_dict.get("event_count", 0)),
            float(window_dict.get("error_rate", 0.0)),
            float(window_dict.get("average_latency_ms", 0.0)),
        ]

    def fit(self, baseline_windows: List[Dict[str, Any]]) -> bool:
        """
        Fit Isolation Forest model on historical baseline metric windows.
        Requires at least 3 samples to construct an ensemble tree.
        """
        if not baseline_windows or len(baseline_windows) < 3:
            logger.debug(
                f"Insufficient baseline samples ({len(baseline_windows) if baseline_windows else 0}) for Isolation Forest"
            )
            self.model = None
            return False

        X = np.array([self.extract_features(w) for w in baseline_windows])

        # Adjust contamination if sample size is very small
        effective_contamination = min(self.contamination, 0.5)

        self.model = IsolationForest(
            contamination=effective_contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
        )
        self.model.fit(X)
        return True

    def predict_window(self, current_window: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Evaluate current window vector against trained Isolation Forest.

        Returns:
            Tuple of (is_anomaly, isolation_score)
            - is_anomaly: True if classified as outlier (-1)
            - isolation_score: Decision function score (negative indicates outlier)
        """
        if self.model is None:
            # Neutral result if model is not trained
            return False, 0.0

        vec = np.array([self.extract_features(current_window)])
        prediction = self.model.predict(vec)[0]  # -1 = anomaly, 1 = normal
        score = self.model.decision_function(vec)[0]

        is_anomaly = bool(prediction == -1)
        return is_anomaly, round(float(score), 3)

    def detect(
        self,
        baseline_windows: List[Dict[str, Any]],
        current_window: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Convenience execution routine: trains on dataset (baseline + current)
        and scores the current window.
        """
        all_windows = list(baseline_windows) + [current_window]
        is_fitted = self.fit(all_windows)
        if not is_fitted:
            return {
                "is_anomaly": False,
                "isolation_score": 0.0,
                "fitted": False,
            }

        is_anomaly, score = self.predict_window(current_window)
        return {
            "is_anomaly": is_anomaly,
            "isolation_score": score,
            "fitted": True,
        }
