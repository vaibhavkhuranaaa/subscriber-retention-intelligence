import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evaluate_churn_models import (
    CALIBRATION_BUCKETS,
    FEATURE_SQL,
    FIT_BUCKETS,
    FORBIDDEN_MODEL_FEATURES,
    MODEL_FEATURES,
    _array,
    expected_calibration_error,
    ship_challenger,
    top_decile_lift,
    validate_probabilities,
)


class ModelEvaluationTests(unittest.TestCase):
    def test_model_feature_allow_list_excludes_leakage_and_demographics(self):
        self.assertFalse(set(MODEL_FEATURES) & FORBIDDEN_MODEL_FEATURES)

    def test_fit_and_calibration_membership_are_disjoint(self):
        self.assertFalse(set(FIT_BUCKETS) & set(CALIBRATION_BUCKETS))

    def test_feature_sql_enforces_cutoff_dates(self):
        normalized = " ".join(FEATURE_SQL.split())
        self.assertIn("latest_transaction_date <= s.history_cutoff", normalized)
        self.assertIn("latest_activity_date <= s.history_cutoff", normalized)

    def test_expected_calibration_error_is_zero_for_matched_bins(self):
        target = np.array([0, 0, 1, 1], dtype=np.int8)
        probability = np.array([0.0, 0.0, 1.0, 1.0])
        self.assertEqual(expected_calibration_error(target, probability), 0.0)

    def test_masked_integer_can_become_float_missing_value(self):
        values = np.ma.array([1, 2], mask=[False, True])
        converted = _array(values, np.dtype("float32"))
        self.assertEqual(converted[0], 1.0)
        self.assertTrue(np.isnan(converted[1]))

    def test_top_decile_is_exact_and_tie_safe(self):
        target = np.array([1] + [0] * 9, dtype=np.int8)
        probability = np.ones(10) * 0.5
        lift, selected, selected_rate = top_decile_lift(target, probability, np.arange(10))
        self.assertEqual(selected, 1)
        self.assertEqual(selected_rate, 1.0)
        self.assertEqual(lift, 10.0)

    def test_ship_rule_requires_every_gate(self):
        intervals = {
            "relative_log_loss_improvement": [0.01, 0.08],
            "challenger_top_decile_lift": [1.5, 3.0],
        }
        metrics = {"expected_calibration_error": 0.02, "top_decile_lift": 2.5}
        self.assertTrue(ship_challenger(0.06, intervals, metrics))
        self.assertFalse(ship_challenger(0.04, intervals, metrics))

    def test_probability_contract_rejects_bad_count_or_value(self):
        target = np.array([0, 1], dtype=np.int8)
        validate_probabilities(target, np.array([0.1, 0.9]))
        with self.assertRaises(RuntimeError):
            validate_probabilities(target, np.array([0.1]))
        with self.assertRaises(RuntimeError):
            validate_probabilities(target, np.array([0.1, np.nan]))


if __name__ == "__main__":
    unittest.main()
