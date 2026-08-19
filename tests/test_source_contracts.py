import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "profile_sources", ROOT / "scripts/profile_sources.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SourceContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((ROOT / "contracts/sources.json").read_text())

    def test_every_field_has_complete_contract(self):
        complete, required = MODULE.validate_contract(self.contract)
        self.assertEqual(complete, required)
        self.assertGreater(required, 0)

    def test_all_source_archives_are_declared(self):
        names = {archive["name"] for archive in self.contract["archives"]}
        self.assertEqual(
            names,
            {
                "members_v3.csv.7z",
                "train.csv.7z",
                "train_v2.csv.7z",
                "transactions.csv.7z",
                "transactions_v2.csv.7z",
                "user_logs.csv.7z",
                "user_logs_v2.csv.7z",
                "sample_submission_zero.csv.7z",
                "sample_submission_v2.csv.7z",
            },
        )

    def test_churn_boundary_is_thirty_days(self):
        self.assertEqual(MODULE.churn_from_gap(None), 1)
        self.assertEqual(MODULE.churn_from_gap(29), 0)
        self.assertEqual(MODULE.churn_from_gap(30), 1)

    def test_same_day_subscription_precedes_cancellation(self):
        base = {
            "transaction_date": 20170131,
            "plan_list_price": 149,
            "payment_plan_days": 30,
            "payment_method_id": 36,
            "membership_expire_date": 20170228,
        }
        self.assertLess(
            MODULE.transaction_order_key({**base, "is_cancel": 0}),
            MODULE.transaction_order_key({**base, "is_cancel": 1}),
        )

    def test_storage_projection_includes_downstream_allowance(self):
        self.assertEqual(MODULE.projected_storage_gib(10 * MODULE.GIB, 0.1), 11.0)


if __name__ == "__main__":
    unittest.main()
