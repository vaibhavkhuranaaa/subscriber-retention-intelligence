import json
import re
import unittest
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "evaluation/churn-model.json"
MODEL = ROOT.parent / f"{ROOT.name}-ops" / "data/private/models/m6-selected.joblib"


class ModelArtifactTests(unittest.TestCase):
    def test_report_and_artifact_preserve_scope_and_privacy(self):
        report_text = REPORT.read_text()
        report = json.loads(report_text)
        self.assertEqual(report["decision"], "ship_challenger_repeat_only")
        self.assertFalse(report["feature_contract"]["demographics_used_for_scoring"])
        self.assertFalse(report["feature_contract"]["post_cutoff_activity_used"])
        self.assertNotRegex(report_text, re.compile(r"\b[0-9a-f]{24}\b", re.IGNORECASE))
        if MODEL.exists():
            self.assertEqual(joblib.load(MODEL)["eligible_scope"], "repeat_subscribers_only")

    def test_future_test_and_statistical_gates_are_recorded(self):
        report = json.loads(REPORT.read_text())
        self.assertTrue(report["evaluation_contract"]["test"]["untouched_until_final_evaluation"])
        self.assertEqual(report["evaluation_contract"]["test"]["window"], "2017-03")
        self.assertTrue(report["ship_rule"]["overall_gate_passed"])
        self.assertTrue(report["ship_rule"]["repeat_subscriber_gate_passed"])
        self.assertFalse(report["ship_rule"]["march_new_probability_use_allowed"])


if __name__ == "__main__":
    unittest.main()
