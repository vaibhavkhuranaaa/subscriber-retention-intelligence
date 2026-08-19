#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")

import duckdb
import joblib
import numpy as np
from evaluate_churn_models import NUMERIC_FEATURES, load_dataset
from scipy import sparse

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DIR = Path(
    os.getenv("RETENTION_PRIVATE_DIR", ROOT.parent / f"{ROOT.name}-ops" / "data/private")
)
DEFAULT_WAREHOUSE = PRIVATE_DIR / "warehouse/retention.duckdb"
DEFAULT_MODEL = PRIVATE_DIR / "models/m6-selected.joblib"
DEFAULT_OUTPUT = PRIVATE_DIR / "models/m7-scenario-curve.json"
GROUP_SIZE = 100


def model_matrix(dataset, artifact):
    if artifact["selected_model"] == "histogram_gradient_boosting":
        encoded = artifact["categorical_encoder"].transform(dataset.categorical)
        return np.column_stack([dataset.numeric, encoded]).astype(np.float32)
    numeric = np.where(np.isnan(dataset.numeric), artifact["numeric_medians"], dataset.numeric)
    scaled = sparse.csr_matrix(artifact["scaler"].transform(numeric).astype(np.float32))
    encoded = artifact["categorical_encoder"].transform(dataset.categorical)
    return sparse.hstack([scaled, encoded], format="csr")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", type=Path, default=DEFAULT_WAREHOUSE)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    started = time.perf_counter()
    artifact = joblib.load(arguments.model)
    if artifact["eligible_scope"] != "repeat_subscribers_only":
        raise RuntimeError("M7 requires the approved repeat-subscriber model scope")

    connection = duckdb.connect(str(arguments.warehouse), read_only=True)
    connection.execute("set threads = 1")
    connection.execute("set memory_limit = '4GB'")
    dataset = load_dataset(connection, "2017-03", None)
    connection.close()
    probability = artifact["model"].predict_proba(model_matrix(dataset, artifact))[:, 1]
    repeat = dataset.diagnostics["is_repeat_subscriber"] == 1
    probability = probability[repeat]
    target = dataset.target[repeat]
    tie_breaker = dataset.tie_breaker[repeat]
    payment_index = NUMERIC_FEATURES.index("latest_actual_amount_paid")
    receipts = np.maximum(dataset.numeric[repeat, payment_index].astype(np.float64), 0.0)
    order = np.lexsort((tie_breaker, -probability))
    probability = probability[order]
    target = target[order]
    receipts = receipts[order]
    cumulative_expected = np.cumsum(probability, dtype=np.float64)
    cumulative_observed = np.cumsum(target, dtype=np.int64)
    cumulative_risk_value = np.cumsum(probability * receipts, dtype=np.float64)
    cumulative_receipts = np.cumsum(receipts, dtype=np.float64)
    indices = list(range(GROUP_SIZE - 1, len(target), GROUP_SIZE))
    if indices[-1] != len(target) - 1:
        indices.append(len(target) - 1)
    points = [
        {
            "contacts": index + 1,
            "minimum_score": round(float(probability[index]), 8),
            "expected_churners": round(float(cumulative_expected[index]), 4),
            "observed_churners": int(cumulative_observed[index]),
            "risk_weighted_payment_proxy": round(float(cumulative_risk_value[index]), 2),
            "selected_payment_proxy": round(float(cumulative_receipts[index]), 2),
        }
        for index in indices
    ]
    output = {
        "version": "m7.1",
        "status": "ready",
        "scope": "repeat_subscribers_only",
        "score_window": "2017-03",
        "eligible_subscribers": len(target),
        "group_size": GROUP_SIZE,
        "model": artifact["selected_model"],
        "total_expected_churners": round(float(cumulative_expected[-1]), 4),
        "total_risk_weighted_payment_proxy": round(float(cumulative_risk_value[-1]), 2),
        "value_proxy": "Latest nonnegative payment amount, not forecast revenue or lifetime value.",
        "points": points,
        "resource_contract": {
            "duckdb_threads": 1,
            "duckdb_memory_limit_gib": 4,
            "model_threads": 1,
            "docker_used": False,
        },
        "runtime_seconds": time.perf_counter() - started,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(output, separators=(",", ":")) + "\n")
    print(
        json.dumps(
            {
                key: output[key]
                for key in (
                    "status",
                    "scope",
                    "eligible_subscribers",
                    "group_size",
                    "runtime_seconds",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
