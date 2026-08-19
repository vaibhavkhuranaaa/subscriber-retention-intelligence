import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SPEC = importlib.util.spec_from_file_location(
    "build_release_fixture", ROOT / "scripts/build_release_fixture.py"
)
FIXTURE = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(FIXTURE)
VERIFY_SPEC = importlib.util.spec_from_file_location(
    "verify_power_bi_contract", ROOT / "scripts/verify_power_bi_contract.py"
)
VERIFY = importlib.util.module_from_spec(VERIFY_SPEC)
VERIFY_SPEC.loader.exec_module(VERIFY)


class PowerBiContractTests(unittest.TestCase):
    def test_contract_shapes_reconcile_on_clean_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            warehouse = root / "retention.duckdb"
            FIXTURE.build(warehouse, root / "curve.json")
            report = VERIFY.verify(warehouse, ROOT / "powerbi/semantic-contract.json")
            self.assertEqual(report["status"], "passed", report["problems"])
            self.assertEqual(report["contract_reconciliation_pass_rate"], 1.0)
            self.assertEqual(report["power_bi_engine_reconciliation"], "not_run")

    def test_actual_engine_export_must_match_every_control(self):
        expected = [{"control_id": "a", "expected_value": 1.0}]
        with tempfile.TemporaryDirectory() as directory:
            actual = Path(directory) / "actual.csv"
            with actual.open("w", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=["control_id", "actual_value"])
                writer.writeheader()
                writer.writerow({"control_id": "a", "actual_value": 2})
            self.assertEqual(
                VERIFY.compare_controls(expected, actual),
                ["Power BI control mismatch: a"],
            )

    def test_unknown_cohort_and_composite_segment_keys_are_explicit(self):
        contract = (ROOT / "powerbi/semantic-contract.json").read_text()
        self.assertIn("Unknown registration cohort", contract)
        self.assertIn("dimension || ':' || segment_key", contract)


if __name__ == "__main__":
    unittest.main()
