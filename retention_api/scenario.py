from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DIR = Path(
    os.getenv("RETENTION_PRIVATE_DIR", ROOT.parent / f"{ROOT.name}-ops" / "data/private")
)
CURVE_PATH = Path(
    os.getenv("RETENTION_SCENARIO_CURVE_PATH", PRIVATE_DIR / "models/m7-scenario-curve.json")
)


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    capacity: int = Field(ge=0)
    minimum_score: float = Field(ge=0, le=1)
    contact_cost: float = Field(ge=0, le=10_000)
    offer_cost: float = Field(ge=0, le=10_000)
    assumed_lift: float = Field(ge=0, le=1)
    lift_uncertainty: float = Field(ge=0, le=0.5)


@lru_cache(maxsize=1)
def load_curve() -> dict[str, Any]:
    if not CURVE_PATH.exists():
        raise FileNotFoundError("Scenario curve unavailable. Run scripts/build_scenario_curve.py.")
    return json.loads(CURVE_PATH.read_text())


def outcome(
    point: dict[str, float | int],
    lift: float,
    contact_cost: float,
    offer_cost: float,
) -> dict[str, Any]:
    contacts = int(point["contacts"])
    expected_churners = float(point["expected_churners"])
    risk_value = float(point["risk_weighted_payment_proxy"])
    contact_spend = contacts * contact_cost
    offer_spend = contacts * offer_cost
    retained_subscribers = expected_churners * lift
    retained_value = risk_value * lift
    total_spend = contact_spend + offer_spend
    net_value = retained_value - total_spend
    break_even_lift = total_spend / risk_value if risk_value else None
    return {
        "assumed_lift": lift,
        "simulated_retained_subscribers": retained_subscribers,
        "simulated_retained_gross_receipt_proxy": retained_value,
        "contact_spend": contact_spend,
        "offer_spend": offer_spend,
        "total_spend": total_spend,
        "simulated_net_value": net_value,
        "simulated_roi": net_value / total_spend if total_spend else None,
        "break_even_lift": break_even_lift,
        "break_even_feasible": break_even_lift is not None and break_even_lift <= 1,
    }


def calculate_scenario(
    curve: dict[str, Any],
    capacity: int,
    minimum_score: float,
    contact_cost: float,
    offer_cost: float,
    assumed_lift: float,
    lift_uncertainty: float,
) -> dict[str, Any]:
    eligible = int(curve["eligible_subscribers"])
    if capacity < 0 or capacity > eligible:
        raise ValueError(f"capacity must be between 0 and {eligible}")
    if capacity and capacity < int(curve["group_size"]):
        raise ValueError(f"positive capacity must be at least {curve['group_size']}")
    if not 0 <= minimum_score <= 1:
        raise ValueError("minimum_score must be between 0 and 1")
    if not 0 <= assumed_lift <= 1:
        raise ValueError("assumed_lift must be between 0 and 1")
    if not 0 <= lift_uncertainty <= 0.5:
        raise ValueError("lift_uncertainty must be between 0 and 0.5")
    if not 0 <= contact_cost <= 10_000 or not 0 <= offer_cost <= 10_000:
        raise ValueError("costs must be between 0 and 10000")

    selected: dict[str, float | int] = {
        "contacts": 0,
        "minimum_score": minimum_score,
        "expected_churners": 0.0,
        "observed_churners": 0,
        "risk_weighted_payment_proxy": 0.0,
        "selected_payment_proxy": 0.0,
    }
    for point in curve["points"]:
        if int(point["contacts"]) > capacity or float(point["minimum_score"]) < minimum_score:
            break
        selected = point

    lifts = {
        "low": max(0.0, assumed_lift - lift_uncertainty),
        "expected": assumed_lift,
        "high": min(1.0, assumed_lift + lift_uncertainty),
    }
    contacts = int(selected["contacts"])
    observed_churn_rate = float(selected["observed_churners"]) / contacts if contacts else 0.0
    modeled_risk_capture = (
        float(selected["expected_churners"]) / float(curve["total_expected_churners"])
        if contacts
        else 0.0
    )
    return {
        "status": "simulated",
        "scope": curve["scope"],
        "score_window": curve["score_window"],
        "requested": {
            "capacity": capacity,
            "minimum_score": minimum_score,
            "contact_cost": contact_cost,
            "offer_cost": offer_cost,
            "assumed_lift": assumed_lift,
            "lift_uncertainty": lift_uncertainty,
        },
        "selection": {
            **selected,
            "observed_churn_rate": observed_churn_rate,
            "modeled_risk_capture": modeled_risk_capture,
            "capacity_utilization": contacts / capacity if capacity else None,
            "eligible_subscribers": eligible,
            "new_subscribers_excluded": True,
        },
        "outcomes": {
            name: outcome(selected, lift, contact_cost, offer_cost) for name, lift in lifts.items()
        },
        "definitions": {
            "assumed_lift": "User assumption: share of expected churners retained by intervention.",
            "offer_cost": "Conservative cost per contacted subscriber, whether or not retained.",
            "value_proxy": curve["value_proxy"],
            "limitation": "Simulated arithmetic, not observed treatment effect or revenue forecast.",
        },
    }
