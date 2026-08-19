import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("build_facts", ROOT / "scripts/build_facts.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FactPipelineTests(unittest.TestCase):
    def test_disk_pressure_stops_below_reserve_and_allows_boundary(self):
        reserve = 30 * MODULE.GIB
        with self.assertRaisesRegex(RuntimeError, "below"):
            MODULE.require_disk(Path("."), reserve, reserve - 1)
        self.assertEqual(MODULE.require_disk(Path("."), reserve, reserve), reserve)

    def test_header_drift_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "header drift"):
            MODULE.validate_header("a,b", "a,c")
        MODULE.validate_header("a,b", "a,b")

    def test_duplicate_keys_are_rejected(self):
        import duckdb

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "rows.parquet"
            duckdb.sql(
                f"COPY (SELECT * FROM (VALUES ('a', DATE '2017-01-01'), ('a', DATE '2017-01-01')) t(subscriber_token, activity_date)) TO '{path}' (FORMAT PARQUET)"
            )
            with self.assertRaisesRegex(RuntimeError, "duplicate keys"):
                MODULE.assert_unique(
                    duckdb.connect(),
                    str(path),
                    ("subscriber_token", "activity_date"),
                    "listening",
                )

    def test_transaction_exact_duplicates_collapse_without_version_precedence(self):
        import duckdb

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "raw.parquet"
            output = root / "fact.parquet"
            duckdb.sql(
                f"COPY (SELECT * FROM (VALUES "
                "('token', 1, 30, 100, 90, 1, DATE '2017-01-01', DATE '2017-01-31', 0, 'v1'), "
                "('token', 1, 30, 100, 90, 1, DATE '2017-01-01', DATE '2017-01-31', 0, 'v2')) "
                "t(subscriber_token, payment_method_id, payment_plan_days, plan_list_price, actual_amount_paid, is_auto_renew, transaction_date, membership_expire_date, is_cancel, source_version)) "
                f"TO '{raw}' (FORMAT PARQUET)"
            )
            controls = MODULE.build_transactions(duckdb.connect(), str(raw), output)
            self.assertEqual(controls["source_rows"], 2)
            self.assertEqual(controls["accepted_rows"], 1)
            self.assertEqual(controls["cross_version_duplicate_rows_removed"], 1)
            source_versions = duckdb.sql(
                f"SELECT source_versions FROM read_parquet('{output}')"
            ).fetchone()[0]
            self.assertEqual(source_versions, "v1+v2")

    def test_failed_promotion_restores_previous_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = root / "facts"
            stage = root / "stage"
            current.mkdir()
            stage.mkdir()
            (current / "marker").write_text("old")
            (stage / "marker").write_text("new")
            with self.assertRaisesRegex(RuntimeError, "injected"):
                MODULE.promote(stage, current, fail_after_backup=True)
            self.assertEqual((current / "marker").read_text(), "old")

    def test_matching_fingerprint_is_stable_and_changes_with_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = root / "contract.json"
            archive = root / "source.7z"
            contract.write_text(json.dumps({"version": 1}))
            archive.write_bytes(b"one")
            declarations = [{"name": "source.7z", "selected": True}]
            first = MODULE.source_fingerprint(contract, root, declarations)
            second = MODULE.source_fingerprint(contract, root, declarations)
            self.assertEqual(first, second)
            archive.write_bytes(b"changed")
            self.assertNotEqual(first, MODULE.source_fingerprint(contract, root, declarations))

    def test_replay_rejects_missing_or_changed_facts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            controls = {"storage": {"allocated_bytes": 0}}
            with self.assertRaisesRegex(RuntimeError, "incomplete"):
                MODULE.verify_existing_output(root, controls)

    def test_canonical_queries_drop_source_identifier(self):
        contract = json.loads((ROOT / "contracts/sources.json").read_text())
        for family in contract["families"]:
            query = MODULE.conversion_query(contract, family, "v1", "2017-02")
            selected = query.split(" FROM ", 1)[0]
            self.assertNotIn("msno,", selected)
            self.assertIn("unhex(substr(sha256(msno), 1, 24)) AS subscriber_token", selected)

    def test_subscriber_token_is_fixed_width_binary(self):
        import duckdb

        value = duckdb.sql(
            f"SELECT {MODULE.subscriber_token_expression()} FROM (VALUES ('source-id')) t(msno)"
        ).fetchone()[0]
        self.assertIsInstance(value, bytes)
        self.assertEqual(len(value), 12)

    def test_unknown_registration_method_becomes_null(self):
        contract = json.loads((ROOT / "contracts/sources.json").read_text())
        query = MODULE.conversion_query(contract, "members", "", "")
        self.assertIn("nullif(registered_via, -1) AS registration_method_code", query)

    def test_negative_listening_duration_is_flagged_and_canonicalized(self):
        contract = json.loads((ROOT / "contracts/sources.json").read_text())
        query = MODULE.conversion_query(contract, "listening", "v1", "")
        self.assertIn("greatest(total_secs, 0) AS total_secs", query)
        self.assertIn("total_secs < 0 AS total_secs_was_negative", query)


if __name__ == "__main__":
    unittest.main()
