import math
import unittest

from retention_api.scenario import calculate_scenario, outcome

CURVE = {
    "scope": "repeat_subscribers_only",
    "score_window": "2017-03",
    "eligible_subscribers": 300,
    "group_size": 100,
    "total_expected_churners": 90.0,
    "value_proxy": "Latest nonnegative payment amount.",
    "points": [
        {
            "contacts": 100,
            "minimum_score": 0.8,
            "expected_churners": 60.0,
            "observed_churners": 62,
            "risk_weighted_payment_proxy": 6000.0,
            "selected_payment_proxy": 10000.0,
        },
        {
            "contacts": 200,
            "minimum_score": 0.4,
            "expected_churners": 80.0,
            "observed_churners": 84,
            "risk_weighted_payment_proxy": 8000.0,
            "selected_payment_proxy": 20000.0,
        },
        {
            "contacts": 300,
            "minimum_score": 0.1,
            "expected_churners": 90.0,
            "observed_churners": 96,
            "risk_weighted_payment_proxy": 9000.0,
            "selected_payment_proxy": 30000.0,
        },
    ],
}


def scenario(**changes):
    inputs = {
        "capacity": 200,
        "minimum_score": 0.4,
        "contact_cost": 1.0,
        "offer_cost": 4.0,
        "assumed_lift": 0.2,
        "lift_uncertainty": 0.1,
    }
    inputs.update(changes)
    return calculate_scenario(CURVE, **inputs)


class ScenarioTests(unittest.TestCase):
    def test_base_formula_reconciles(self):
        result = scenario()
        expected = result["outcomes"]["expected"]
        self.assertEqual(result["selection"]["contacts"], 200)
        self.assertAlmostEqual(expected["simulated_retained_subscribers"], 16.0)
        self.assertAlmostEqual(expected["simulated_retained_gross_receipt_proxy"], 1600.0)
        self.assertAlmostEqual(expected["total_spend"], 1000.0)
        self.assertAlmostEqual(expected["simulated_net_value"], 600.0)
        self.assertAlmostEqual(expected["break_even_lift"], 0.125)

    def test_zero_capacity_zeroes_every_output(self):
        result = scenario(capacity=0)
        self.assertEqual(result["selection"]["contacts"], 0)
        for bound in result["outcomes"].values():
            for field in (
                "simulated_retained_subscribers",
                "simulated_retained_gross_receipt_proxy",
                "total_spend",
                "simulated_net_value",
            ):
                self.assertEqual(bound[field], 0.0)
            self.assertIsNone(bound["simulated_roi"])
        self.assertIsNone(result["selection"]["capacity_utilization"])

    def test_threshold_and_capacity_are_both_binding(self):
        self.assertEqual(scenario(capacity=300, minimum_score=0.8)["selection"]["contacts"], 100)
        self.assertEqual(scenario(capacity=100, minimum_score=0.0)["selection"]["contacts"], 100)
        self.assertEqual(scenario(capacity=300, minimum_score=1.0)["selection"]["contacts"], 0)

    def test_zero_lift_and_high_cost_remain_negative(self):
        result = scenario(assumed_lift=0, lift_uncertainty=0, contact_cost=100, offer_cost=100)
        expected = result["outcomes"]["expected"]
        self.assertEqual(expected["simulated_retained_subscribers"], 0.0)
        self.assertEqual(expected["simulated_retained_gross_receipt_proxy"], 0.0)
        self.assertEqual(expected["simulated_net_value"], -40000.0)

    def test_uncertainty_clips_and_stays_ordered(self):
        result = scenario(assumed_lift=0.95, lift_uncertainty=0.2)
        values = [
            result["outcomes"][key]["simulated_retained_subscribers"]
            for key in ("low", "expected", "high")
        ]
        self.assertEqual(result["outcomes"]["high"]["assumed_lift"], 1.0)
        self.assertEqual(values, sorted(values))

    def test_zero_value_has_no_retained_value(self):
        point = {
            "contacts": 100,
            "expected_churners": 50.0,
            "risk_weighted_payment_proxy": 0.0,
        }
        result = outcome(point, 0.5, 1.0, 1.0)
        self.assertEqual(result["simulated_retained_gross_receipt_proxy"], 0.0)
        self.assertEqual(result["simulated_net_value"], -200.0)
        self.assertIsNone(result["break_even_lift"])

    def test_invalid_inputs_fail_closed(self):
        for changes in (
            {"capacity": -1},
            {"capacity": 1},
            {"capacity": 301},
            {"minimum_score": math.nan},
            {"minimum_score": -0.1},
            {"assumed_lift": 1.1},
            {"lift_uncertainty": 0.6},
            {"contact_cost": -1},
            {"offer_cost": 10001},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                scenario(**changes)


if __name__ == "__main__":
    unittest.main()
