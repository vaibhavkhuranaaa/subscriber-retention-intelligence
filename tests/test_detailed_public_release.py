import importlib.util
import tempfile
import unittest
from pathlib import Path

import duckdb

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_detailed_public_release", ROOT / "scripts/build_detailed_public_release.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DetailedPublicReleaseTests(unittest.TestCase):
    def test_rekeys_every_row_and_generalizes_member_attributes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            facts = root / "facts"
            token = "unhex('00112233445566778899aabb')"
            event = "unhex('ffeeddccbbaa998877665544')"

            def write(path: Path, query: str) -> None:
                path.parent.mkdir(parents=True, exist_ok=True)
                duckdb.sql(f"COPY ({query}) TO '{path}' (FORMAT PARQUET)")

            write(
                facts / "dim_member/data.parquet",
                f"select {token} subscriber_token, 1 city_code, 37 age_reported, "
                "'female' gender, 7 registration_method_code, date '2017-01-19' registration_date",
            )
            write(
                facts / "fact_subscription_transaction/data.parquet",
                f"select {event} event_key, {token} subscriber_token, 1 payment_method_id, "
                "30 payment_plan_days, 100 plan_list_price, 90 actual_amount_paid, "
                "1::utinyint is_auto_renew, date '2017-01-01' transaction_date, "
                "date '2017-01-31' membership_expire_date, 0::utinyint is_cancel, 'v1' source_versions",
            )
            for window in ("2017-02", "2017-03"):
                write(
                    facts / f"fact_churn_label/window={window}/data.parquet",
                    f"select {token} subscriber_token, '{window}' label_window, 0::utinyint is_churn",
                )
            write(
                facts
                / "fact_listening_day/source_version=v1/activity_month=201701/data.parquet",
                f"select {token} subscriber_token, date '2017-01-01' activity_date, "
                "1 num_25, 2 num_50, 3 num_75, 4 num_985, 5 num_100, 6 num_unq, "
                "7.0 total_secs, false total_secs_was_negative, 'v1' source_version",
            )

            output = root / "release"
            manifest = MODULE.build(facts, output, root / "salt", "test-release")
            self.assertEqual(manifest["rows"], 5)
            database = duckdb.connect()
            member = database.execute(
                f"select * from read_parquet('{output / 'member/data.parquet'}')"
            ).fetchone()
            columns = [item[0] for item in database.description]
            self.assertNotIn("age_reported", columns)
            self.assertNotIn("registration_date", columns)
            self.assertEqual(member[columns.index("age_band_start")], 30)
            self.assertEqual(str(member[columns.index("registration_month")]), "2017-01-01")
            private = duckdb.sql(f"select {token}").fetchone()[0]
            public = member[columns.index("subscriber_key")]
            self.assertNotEqual(public, private)
            transaction_public = database.execute(
                f"select subscriber_key from read_parquet('{output / 'subscription_transaction/**/*.parquet'}')"
            ).fetchone()[0]
            self.assertEqual(public, transaction_public)


if __name__ == "__main__":
    unittest.main()
