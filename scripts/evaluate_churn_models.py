#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")

import duckdb
import joblib
import numpy as np
from scipy import sparse
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = Path(
    os.getenv("RETENTION_EVIDENCE_DIR", ROOT.parent / f"{ROOT.name}-ops" / "evidence")
)
PRIVATE_DIR = Path(
    os.getenv("RETENTION_PRIVATE_DIR", ROOT.parent / f"{ROOT.name}-ops" / "data/private")
)
DEFAULT_WAREHOUSE = PRIVATE_DIR / "warehouse/retention.duckdb"
DEFAULT_REPORT = EVIDENCE_DIR / "m6-model-evaluation.json"
DEFAULT_MODEL = PRIVATE_DIR / "models/m6-selected.joblib"
FIT_BUCKETS = (0, 1)
CALIBRATION_BUCKETS = (2,)
RANDOM_SEED = 731
BOOTSTRAP_REPLICATES = 100
BOOTSTRAP_SAMPLE = 250_000
MIN_SUBGROUP_ROWS = 1_000

NUMERIC_FEATURES = (
    "tenure_days",
    "invalid_registration",
    "missing_registration",
    "log_subscription_events_lifetime",
    "log_subscription_events_30d",
    "log_subscription_events_90d",
    "log_gross_receipts_lifetime",
    "log_gross_receipts_30d",
    "log_gross_receipts_90d",
    "log_cancellation_events_lifetime",
    "log_cancellation_events_30d",
    "days_since_transaction",
    "days_to_expiration",
    "latest_plan_list_price",
    "latest_actual_amount_paid",
    "listening_active_days_30d",
    "listening_active_days_90d",
    "log_listening_seconds_30d",
    "log_listening_seconds_90d",
    "log_unique_tracks_30d",
    "log_unique_tracks_90d",
    "log_full_completions_30d",
    "log_full_completions_90d",
    "log_play_count_30d",
    "log_play_count_90d",
    "days_since_activity",
    "negative_duration_rows_90d",
    "missing_transaction",
    "missing_listening",
)
CATEGORICAL_FEATURES = (
    "registration_method_code",
    "latest_payment_method_id",
    "latest_payment_plan_days",
    "latest_is_auto_renew",
    "latest_is_cancel",
    "is_active_at_cutoff",
    "engagement_segment_code",
)
MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
FORBIDDEN_MODEL_FEATURES = {
    "subscriber_token",
    "is_churn",
    "observed_renewed_within_30_days",
    "label_window",
    "history_cutoff",
    "expiration_window_start",
    "expiration_window_end",
    "renewal_observation_end",
    "registration_date",
    "latest_transaction_date",
    "effective_expiration_date",
    "latest_activity_date",
    "age_reported",
    "gender",
    "city_code",
    "is_repeat_subscriber",
}

FEATURE_SQL = """
with february_members as (
    select subscriber_token
    from fct_subscriber_snapshot
    where label_window = '2017-02'
)
select
    case when registration_date is not null and registration_date <= history_cutoff
        then date_diff('day', registration_date, history_cutoff) else null end as tenure_days,
    cast(registration_date > history_cutoff as integer) as invalid_registration,
    cast(registration_date is null as integer) as missing_registration,
    ln(1 + greatest(subscription_event_count_lifetime, 0)) as log_subscription_events_lifetime,
    ln(1 + greatest(subscription_event_count_30d, 0)) as log_subscription_events_30d,
    ln(1 + greatest(subscription_event_count_90d, 0)) as log_subscription_events_90d,
    ln(1 + greatest(gross_receipts_lifetime, 0)) as log_gross_receipts_lifetime,
    ln(1 + greatest(gross_receipts_30d, 0)) as log_gross_receipts_30d,
    ln(1 + greatest(gross_receipts_90d, 0)) as log_gross_receipts_90d,
    ln(1 + greatest(cancellation_event_count_lifetime, 0)) as log_cancellation_events_lifetime,
    ln(1 + greatest(cancellation_event_count_30d, 0)) as log_cancellation_events_30d,
    coalesce(date_diff('day', latest_transaction_date, history_cutoff), 9999) as days_since_transaction,
    coalesce(date_diff('day', history_cutoff, effective_expiration_date), -9999) as days_to_expiration,
    coalesce(latest_plan_list_price, 0) as latest_plan_list_price,
    coalesce(latest_actual_amount_paid, 0) as latest_actual_amount_paid,
    listening_active_days_30d,
    listening_active_days_90d,
    ln(1 + greatest(listening_seconds_30d, 0)) as log_listening_seconds_30d,
    ln(1 + greatest(listening_seconds_90d, 0)) as log_listening_seconds_90d,
    ln(1 + greatest(unique_track_count_30d, 0)) as log_unique_tracks_30d,
    ln(1 + greatest(unique_track_count_90d, 0)) as log_unique_tracks_90d,
    ln(1 + greatest(full_completion_count_30d, 0)) as log_full_completions_30d,
    ln(1 + greatest(full_completion_count_90d, 0)) as log_full_completions_90d,
    ln(1 + greatest(play_count_30d, 0)) as log_play_count_30d,
    ln(1 + greatest(play_count_90d, 0)) as log_play_count_90d,
    coalesce(date_diff('day', latest_activity_date, history_cutoff), 9999) as days_since_activity,
    negative_duration_rows_90d,
    cast(latest_transaction_date is null as integer) as missing_transaction,
    cast(latest_activity_date is null as integer) as missing_listening,
    case when registration_date is null or registration_date > history_cutoff then -1
        else coalesce(registration_method_code, -1) end as registration_method_code,
    coalesce(latest_payment_method_id, -1) as latest_payment_method_id,
    coalesce(latest_payment_plan_days, -1) as latest_payment_plan_days,
    coalesce(latest_is_auto_renew, 2) as latest_is_auto_renew,
    coalesce(latest_is_cancel, 2) as latest_is_cancel,
    cast(is_active_at_cutoff as integer) as is_active_at_cutoff,
    case engagement_segment when 'Dormant' then 0 when 'Light' then 1
        when 'Steady' then 2 when 'High' then 3 else -1 end as engagement_segment_code,
    is_churn,
    hash(subscriber_token) as tie_breaker,
    cast(f.subscriber_token is not null as integer) as is_repeat_subscriber,
    coalesce(cast(latest_is_auto_renew as integer), 2) as diagnostic_auto_renew,
    case engagement_segment when 'Dormant' then 0 when 'Light' then 1
        when 'Steady' then 2 when 'High' then 3 else -1 end as diagnostic_engagement,
    case when age_reported between 10 and 24 then 1 when age_reported between 25 and 34 then 2
        when age_reported between 35 and 49 then 3 when age_reported between 50 and 80 then 4 else 0 end as diagnostic_age_band,
    case lower(coalesce(gender, '')) when 'male' then 1 when 'female' then 2 else 0 end as diagnostic_gender
from fct_subscriber_snapshot s
left join february_members f using (subscriber_token)
where s.label_window = ?
  and (s.latest_transaction_date is null or s.latest_transaction_date <= s.history_cutoff)
  and (s.latest_activity_date is null or s.latest_activity_date <= s.history_cutoff)
  {split_filter}
order by hash(s.subscriber_token)
"""


@dataclass
class Dataset:
    numeric: np.ndarray
    categorical: np.ndarray
    target: np.ndarray
    tie_breaker: np.ndarray
    diagnostics: dict[str, np.ndarray]

    def __len__(self) -> int:
        return len(self.target)


def _array(values: np.ndarray, dtype: np.dtype[Any]) -> np.ndarray:
    if np.ma.isMaskedArray(values):
        fill = np.nan if np.issubdtype(dtype, np.floating) else -1
        values = values.astype(dtype).filled(fill)
    return np.asarray(values, dtype=dtype)


def load_dataset(
    connection: duckdb.DuckDBPyConnection, window: str, buckets: tuple[int, ...] | None
) -> Dataset:
    split_filter = ""
    if buckets is not None:
        split_filter = f"and hash(s.subscriber_token) % 10 in ({','.join(map(str, buckets))})"
    result = connection.execute(
        FEATURE_SQL.format(split_filter=split_filter), [window]
    ).fetchnumpy()
    numeric = np.column_stack(
        [_array(result[name], np.dtype("float32")) for name in NUMERIC_FEATURES]
    )
    categorical = np.column_stack(
        [_array(result[name], np.dtype("int32")) for name in CATEGORICAL_FEATURES]
    )
    return Dataset(
        numeric=numeric,
        categorical=categorical,
        target=_array(result["is_churn"], np.dtype("int8")),
        tie_breaker=_array(result["tie_breaker"], np.dtype("uint64")),
        diagnostics={
            name: _array(result[name], np.dtype("int8"))
            for name in (
                "is_repeat_subscriber",
                "diagnostic_auto_renew",
                "diagnostic_engagement",
                "diagnostic_age_band",
                "diagnostic_gender",
            )
        },
    )


def expected_calibration_error(
    target: np.ndarray, probability: np.ndarray, bins: int = 10
) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    assignment = np.minimum(np.digitize(probability, edges[1:-1]), bins - 1)
    error = 0.0
    for index in range(bins):
        selected = assignment == index
        if selected.any():
            error += selected.mean() * abs(target[selected].mean() - probability[selected].mean())
    return float(error)


def top_decile_lift(
    target: np.ndarray, probability: np.ndarray, tie_breaker: np.ndarray
) -> tuple[float, int, float]:
    count = max(1, math.ceil(len(target) * 0.10))
    order = np.lexsort((tie_breaker, -probability))[:count]
    selected_rate = float(target[order].mean())
    population_rate = float(target.mean())
    return selected_rate / population_rate, count, selected_rate


def metric_set(
    target: np.ndarray, probability: np.ndarray, tie_breaker: np.ndarray
) -> dict[str, float | int]:
    lift, selected, selected_rate = top_decile_lift(target, probability, tie_breaker)
    return {
        "rows": len(target),
        "churn_rate": float(target.mean()),
        "log_loss": float(log_loss(target, probability, labels=[0, 1])),
        "expected_calibration_error": expected_calibration_error(target, probability),
        "top_decile_lift": lift,
        "top_decile_rows": selected,
        "top_decile_churn_rate": selected_rate,
        "average_probability": float(probability.mean()),
    }


def validate_probabilities(target: np.ndarray, probability: np.ndarray) -> None:
    if len(probability) != len(target):
        raise RuntimeError("Prediction count does not match target count")
    if not np.isfinite(probability).all() or (probability < 0).any() or (probability > 1).any():
        raise RuntimeError("Predicted probabilities must be finite and inside [0, 1]")


def stratified_sample(target: np.ndarray, size: int, random: np.random.Generator) -> np.ndarray:
    if size >= len(target):
        return np.arange(len(target))
    positive = np.flatnonzero(target == 1)
    negative = np.flatnonzero(target == 0)
    positive_size = round(size * len(positive) / len(target))
    return np.concatenate(
        [
            random.choice(positive, positive_size, replace=False),
            random.choice(negative, size - positive_size, replace=False),
        ]
    )


def bootstrap_intervals(
    target: np.ndarray,
    baseline_probability: np.ndarray,
    challenger_probability: np.ndarray,
    tie_breaker: np.ndarray,
) -> dict[str, list[float]]:
    random = np.random.default_rng(RANDOM_SEED)
    fixed = stratified_sample(target, min(BOOTSTRAP_SAMPLE, len(target)), random)
    values = {
        name: []
        for name in (
            "relative_log_loss_improvement",
            "baseline_log_loss",
            "challenger_log_loss",
            "challenger_ece",
            "challenger_top_decile_lift",
        )
    }
    for _ in range(BOOTSTRAP_REPLICATES):
        sampled = random.choice(fixed, len(fixed), replace=True)
        sample_target = target[sampled]
        baseline_loss = log_loss(sample_target, baseline_probability[sampled], labels=[0, 1])
        challenger_loss = log_loss(sample_target, challenger_probability[sampled], labels=[0, 1])
        values["relative_log_loss_improvement"].append(
            (baseline_loss - challenger_loss) / baseline_loss
        )
        values["baseline_log_loss"].append(baseline_loss)
        values["challenger_log_loss"].append(challenger_loss)
        values["challenger_ece"].append(
            expected_calibration_error(sample_target, challenger_probability[sampled])
        )
        values["challenger_top_decile_lift"].append(
            top_decile_lift(sample_target, challenger_probability[sampled], tie_breaker[sampled])[0]
        )
    return {
        name: [float(np.quantile(result, 0.025)), float(np.quantile(result, 0.975))]
        for name, result in values.items()
    }


def ship_challenger(
    relative_improvement: float,
    intervals: dict[str, list[float]],
    metrics: dict[str, Any],
) -> bool:
    return (
        relative_improvement >= 0.05
        and intervals["relative_log_loss_improvement"][0] > 0
        and metrics["expected_calibration_error"] <= 0.03
        and metrics["top_decile_lift"] >= 2.0
        and intervals["challenger_top_decile_lift"][0] > 1.0
    )


def subgroup_report(
    dataset: Dataset,
    baseline_probability: np.ndarray,
    challenger_probability: np.ndarray,
) -> dict[str, Any]:
    labels = {
        "is_repeat_subscriber": {0: "march_new", 1: "repeat"},
        "diagnostic_auto_renew": {0: "off", 1: "on", 2: "missing"},
        "diagnostic_engagement": {
            -1: "unknown",
            0: "dormant",
            1: "light",
            2: "steady",
            3: "high",
        },
        "diagnostic_age_band": {
            0: "unknown_or_invalid",
            1: "10_24",
            2: "25_34",
            3: "35_49",
            4: "50_80",
        },
        "diagnostic_gender": {0: "unknown", 1: "male", 2: "female"},
    }
    report: dict[str, Any] = {}
    for field, values in dataset.diagnostics.items():
        groups: dict[str, Any] = {}
        for value in np.unique(values):
            selected = values == value
            if selected.sum() < MIN_SUBGROUP_ROWS:
                continue
            name = labels[field].get(int(value), str(int(value)))
            baseline = metric_set(
                dataset.target[selected],
                baseline_probability[selected],
                dataset.tie_breaker[selected],
            )
            challenger = metric_set(
                dataset.target[selected],
                challenger_probability[selected],
                dataset.tie_breaker[selected],
            )
            groups[name] = {
                "rows": int(selected.sum()),
                "churn_rate": float(dataset.target[selected].mean()),
                "baseline_log_loss": baseline["log_loss"],
                "baseline_ece": baseline["expected_calibration_error"],
                "baseline_top_decile_lift": baseline["top_decile_lift"],
                "challenger_log_loss": challenger["log_loss"],
                "challenger_ece": challenger["expected_calibration_error"],
                "challenger_top_decile_lift": challenger["top_decile_lift"],
            }
        report[field] = groups
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", type=Path, default=DEFAULT_WAREHOUSE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    arguments = parser.parse_args()
    started = time.perf_counter()
    if set(MODEL_FEATURES) & FORBIDDEN_MODEL_FEATURES:
        raise RuntimeError("Forbidden model feature entered the allow-list")

    connection = duckdb.connect(str(arguments.warehouse), read_only=True)
    connection.execute("set threads = 1")
    connection.execute("set memory_limit = '4GB'")
    fit = load_dataset(connection, "2017-02", FIT_BUCKETS)
    calibration = load_dataset(connection, "2017-02", CALIBRATION_BUCKETS)
    test = load_dataset(connection, "2017-03", None)
    connection.close()

    numeric_medians = np.nanmedian(fit.numeric, axis=0)

    def imputed_numeric(dataset: Dataset) -> np.ndarray:
        return np.where(np.isnan(dataset.numeric), numeric_medians, dataset.numeric)

    scaler = StandardScaler().fit(imputed_numeric(fit))
    one_hot = OneHotEncoder(handle_unknown="ignore", sparse_output=True, dtype=np.float32).fit(
        fit.categorical
    )

    def logistic_matrix(dataset: Dataset) -> sparse.csr_matrix:
        numeric = sparse.csr_matrix(scaler.transform(imputed_numeric(dataset)).astype(np.float32))
        return sparse.hstack([numeric, one_hot.transform(dataset.categorical)], format="csr")

    fit_logistic = logistic_matrix(fit)
    calibration_logistic = logistic_matrix(calibration)
    test_logistic = logistic_matrix(test)
    logistic = LogisticRegression(
        C=1.0, max_iter=250, solver="lbfgs", n_jobs=1, random_state=RANDOM_SEED
    )
    logistic.fit(fit_logistic, fit.target)
    calibrated_logistic = CalibratedClassifierCV(FrozenEstimator(logistic), method="sigmoid")
    calibrated_logistic.fit(calibration_logistic, calibration.target)
    baseline_probability = calibrated_logistic.predict_proba(test_logistic)[:, 1]
    validate_probabilities(test.target, baseline_probability)

    ordinal = OrdinalEncoder(
        handle_unknown="use_encoded_value", unknown_value=-1, dtype=np.float32
    ).fit(fit.categorical)

    def challenger_matrix(dataset: Dataset) -> np.ndarray:
        return np.column_stack([dataset.numeric, ordinal.transform(dataset.categorical)]).astype(
            np.float32
        )

    categorical_mask = [False] * len(NUMERIC_FEATURES) + [True] * len(CATEGORICAL_FEATURES)
    fit_challenger = challenger_matrix(fit)
    calibration_challenger = challenger_matrix(calibration)
    test_challenger = challenger_matrix(test)
    challenger = HistGradientBoostingClassifier(
        learning_rate=0.08,
        max_iter=80,
        max_leaf_nodes=15,
        min_samples_leaf=100,
        l2_regularization=0.1,
        categorical_features=categorical_mask,
        random_state=RANDOM_SEED,
    )
    challenger.fit(fit_challenger, fit.target)
    calibrated_challenger = CalibratedClassifierCV(FrozenEstimator(challenger), method="sigmoid")
    calibrated_challenger.fit(calibration_challenger, calibration.target)
    challenger_probability = calibrated_challenger.predict_proba(test_challenger)[:, 1]
    validate_probabilities(test.target, challenger_probability)

    reference_probability = np.full(len(test), fit.target.mean(), dtype=np.float64)
    reference_metrics = metric_set(test.target, reference_probability, test.tie_breaker)
    baseline_metrics = metric_set(test.target, baseline_probability, test.tie_breaker)
    challenger_metrics = metric_set(test.target, challenger_probability, test.tie_breaker)
    relative_improvement = (
        baseline_metrics["log_loss"] - challenger_metrics["log_loss"]
    ) / baseline_metrics["log_loss"]
    intervals = bootstrap_intervals(
        test.target, baseline_probability, challenger_probability, test.tie_breaker
    )
    subgroups = subgroup_report(test, baseline_probability, challenger_probability)
    repeat_mask = test.diagnostics["is_repeat_subscriber"] == 1
    repeat_baseline = metric_set(
        test.target[repeat_mask],
        baseline_probability[repeat_mask],
        test.tie_breaker[repeat_mask],
    )
    repeat_challenger = metric_set(
        test.target[repeat_mask],
        challenger_probability[repeat_mask],
        test.tie_breaker[repeat_mask],
    )
    repeat_improvement = (
        repeat_baseline["log_loss"] - repeat_challenger["log_loss"]
    ) / repeat_baseline["log_loss"]
    repeat_intervals = bootstrap_intervals(
        test.target[repeat_mask],
        baseline_probability[repeat_mask],
        challenger_probability[repeat_mask],
        test.tie_breaker[repeat_mask],
    )
    overall_gate = ship_challenger(relative_improvement, intervals, challenger_metrics)
    repeat_gate = ship_challenger(repeat_improvement, repeat_intervals, repeat_challenger)
    new_ece = subgroups["is_repeat_subscriber"]["march_new"]["challenger_ece"]
    challenger_ships = overall_gate and repeat_gate
    selected_name = "histogram_gradient_boosting" if challenger_ships else "logistic_regression"
    decision = (
        "ship_challenger_repeat_only"
        if challenger_ships and new_ece > 0.03
        else "ship_challenger"
        if challenger_ships
        else "retain_baseline"
    )
    selected_scope = (
        "repeat_subscribers_only"
        if decision == "ship_challenger_repeat_only"
        else "all_label_eligible_subscribers"
    )
    selected_probability = challenger_probability if challenger_ships else baseline_probability
    top_count = math.ceil(len(test) * 0.10)
    top_order = np.lexsort((test.tie_breaker, -challenger_probability))[:top_count]
    top_new_share = float((test.diagnostics["is_repeat_subscriber"][top_order] == 0).mean())

    report = {
        "status": "passed",
        "decision": decision,
        "selected_model": selected_name,
        "selected_scope": selected_scope,
        "evaluation_contract": {
            "fit": {
                "window": "2017-02",
                "hash_buckets": list(FIT_BUCKETS),
                "rows": len(fit),
                "churn_rate": float(fit.target.mean()),
            },
            "calibration": {
                "window": "2017-02",
                "hash_buckets": list(CALIBRATION_BUCKETS),
                "rows": len(calibration),
                "churn_rate": float(calibration.target.mean()),
                "limitation": "Disjoint cross-sectional holdout, not a third temporal cutoff.",
            },
            "test": {
                "window": "2017-03",
                "rows": len(test),
                "churn_rate": float(test.target.mean()),
                "untouched_until_final_evaluation": True,
            },
            "unused_february_hash_buckets": [3, 4, 5, 6, 7, 8, 9],
            "reason": "Fixed bounded cohorts reduce local compute; current source has only two observed label windows.",
        },
        "feature_contract": {
            "features": list(MODEL_FEATURES),
            "forbidden": sorted(FORBIDDEN_MODEL_FEATURES),
            "demographics_used_for_scoring": False,
            "post_cutoff_activity_used": False,
        },
        "models": {
            "prevalence_reference": reference_metrics,
            "logistic_regression": baseline_metrics,
            "histogram_gradient_boosting": challenger_metrics,
        },
        "relative_log_loss_improvement": float(relative_improvement),
        "intervals_95": intervals,
        "repeat_subscriber_evaluation": {
            "relative_log_loss_improvement": float(repeat_improvement),
            "baseline": repeat_baseline,
            "challenger": repeat_challenger,
            "intervals_95": repeat_intervals,
        },
        "subgroups": subgroups,
        "top_decile_composition": {
            "march_new_share": top_new_share,
            "repeat_share": 1.0 - top_new_share,
        },
        "selected_model_metrics": metric_set(test.target, selected_probability, test.tie_breaker),
        "ship_rule": {
            "relative_log_loss_improvement_minimum": 0.05,
            "improvement_interval_lower_bound_above_zero": True,
            "expected_calibration_error_maximum": 0.03,
            "top_decile_lift_minimum": 2.0,
            "lift_interval_lower_bound_above_one": True,
            "overall_gate_passed": overall_gate,
            "repeat_subscriber_gate_passed": repeat_gate,
            "march_new_ece": new_ece,
            "march_new_probability_use_allowed": new_ece <= 0.03,
            "passed_with_scope": challenger_ships,
        },
        "bootstrap": {
            "seed": RANDOM_SEED,
            "replicates": BOOTSTRAP_REPLICATES,
            "fixed_stratified_sample_rows": BOOTSTRAP_SAMPLE,
        },
        "resource_contract": {
            "duckdb_threads": 1,
            "duckdb_memory_limit_gib": 4,
            "model_threads": 1,
            "docker_used": False,
        },
        "runtime_seconds": time.perf_counter() - started,
        "limitations": [
            "Only two observed label windows exist; calibration is disjoint but not temporally later than fitting.",
            "February and March populations shift materially, especially for March-new subscribers.",
            "Historical risk association does not measure intervention effect.",
        ],
    }
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    arguments.report.write_text(json.dumps(report, indent=2) + "\n")
    arguments.model.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "selected_model": selected_name,
            "model": calibrated_challenger if challenger_ships else calibrated_logistic,
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "scaler": None if challenger_ships else scaler,
            "numeric_medians": None if challenger_ships else numeric_medians,
            "categorical_encoder": ordinal if challenger_ships else one_hot,
            "decision_threshold": None,
            "evaluation_window": "2017-03",
            "eligible_scope": selected_scope,
            "eligibility_rule": "is_repeat_subscriber = 1"
            if selected_scope == "repeat_subscribers_only"
            else "label eligible",
        },
        arguments.model,
        compress=3,
    )
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "status",
                    "decision",
                    "selected_model",
                    "relative_log_loss_improvement",
                    "runtime_seconds",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
