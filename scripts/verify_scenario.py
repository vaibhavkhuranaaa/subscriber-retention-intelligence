#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = Path(
    os.getenv("RETENTION_EVIDENCE_DIR", ROOT.parent / f"{ROOT.name}-ops" / "evidence")
)
sys.path.insert(0, str(ROOT))

from retention_api.scenario import calculate_scenario, load_curve, outcome


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=EVIDENCE_DIR / "m7-scenario-tests.txt")
    arguments = parser.parse_args()
    curve = load_curve()
    base = {
        "capacity": 50_000,
        "minimum_score": 0.1,
        "contact_cost": 0.5,
        "offer_cost": 2.0,
        "assumed_lift": 0.12,
        "lift_uncertainty": 0.04,
    }
    checks: list[tuple[str, bool]] = []
    errors: list[float] = []

    scenario = calculate_scenario(curve, **base)
    selection = scenario["selection"]
    for name, result in scenario["outcomes"].items():
        expected_retained = selection["expected_churners"] * result["assumed_lift"]
        expected_value = selection["risk_weighted_payment_proxy"] * result["assumed_lift"]
        expected_spend = selection["contacts"] * (base["contact_cost"] + base["offer_cost"])
        expected_net = expected_value - expected_spend
        case_errors = [
            abs(result["simulated_retained_subscribers"] - expected_retained),
            abs(result["simulated_retained_gross_receipt_proxy"] - expected_value),
            abs(result["total_spend"] - expected_spend),
            abs(result["simulated_net_value"] - expected_net),
        ]
        errors.extend(case_errors)
        checks.append((f"formula_{name}", all(error <= 1e-9 for error in case_errors)))

    zero_capacity = calculate_scenario(curve, **{**base, "capacity": 0})
    checks.append(
        (
            "zero_capacity",
            zero_capacity["selection"]["contacts"] == 0
            and zero_capacity["outcomes"]["expected"]["simulated_net_value"] == 0,
        )
    )
    zero_lift = calculate_scenario(curve, **{**base, "assumed_lift": 0, "lift_uncertainty": 0})
    checks.append(
        (
            "zero_lift",
            zero_lift["outcomes"]["expected"]["simulated_net_value"]
            == -zero_lift["outcomes"]["expected"]["total_spend"],
        )
    )
    threshold_one = calculate_scenario(curve, **{**base, "minimum_score": 1})
    checks.append(("threshold_one", threshold_one["selection"]["contacts"] == 0))
    full = calculate_scenario(
        curve, **{**base, "capacity": curve["eligible_subscribers"], "minimum_score": 0}
    )
    checks.append(
        (
            "full_capacity",
            full["selection"]["contacts"] == curve["eligible_subscribers"],
        )
    )
    high_cost = calculate_scenario(curve, **{**base, "contact_cost": 10_000, "offer_cost": 10_000})
    checks.append(
        (
            "high_cost_negative",
            high_cost["outcomes"]["expected"]["simulated_net_value"] < 0,
        )
    )
    zero_value = outcome(
        {
            "contacts": 100,
            "expected_churners": 50.0,
            "risk_weighted_payment_proxy": 0.0,
        },
        0.5,
        1.0,
        1.0,
    )
    checks.append(
        (
            "zero_value",
            zero_value["simulated_retained_gross_receipt_proxy"] == 0
            and zero_value["simulated_net_value"] == -200,
        )
    )
    uncertainty = [
        scenario["outcomes"][name]["simulated_retained_subscribers"]
        for name in ("low", "expected", "high")
    ]
    checks.append(("ordered_uncertainty", uncertainty == sorted(uncertainty)))
    checks.append(
        (
            "repeat_only",
            curve["scope"] == "repeat_subscribers_only"
            and curve["eligible_subscribers"] == 881_701,
        )
    )

    maximum_error = max(errors, default=0.0)
    passed = all(result for _, result in checks) and maximum_error <= 1e-6
    lines = [
        f"status={'passed' if passed else 'failed'}",
        f"maximum_absolute_reconciliation_error={maximum_error:.12f}",
        f"eligible_repeat_subscribers={curve['eligible_subscribers']}",
        f"curve_build_runtime_seconds={curve['runtime_seconds']:.6f}",
        "docker_used=false",
        "duckdb_threads=1",
        "model_threads=1",
        *(f"{name}={'passed' if result else 'failed'}" for name, result in checks),
    ]
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
