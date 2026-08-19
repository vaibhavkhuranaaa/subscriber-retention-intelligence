import os
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault(
    "RETENTION_WAREHOUSE_PATH",
    str(ROOT.parent / f"{ROOT.name}-ops" / "data/private/warehouse/retention.duckdb"),
)

from retention_api.main import create_app


class ApiTests(unittest.TestCase):
    def test_public_router_has_no_subscriber_routes(self):
        paths = {route.path for route in create_app("public").routes}
        self.assertNotIn("/api/v1/subscribers", paths)
        self.assertNotIn("/api/v1/subscribers/{subscriber_token}", paths)
        self.assertNotIn("/api/v1/scenario", paths)

    def test_public_status_reports_public_mode(self):
        response = TestClient(create_app("public")).get("/api/v1/status")
        self.assertEqual(response.json()["meta"]["mode"], "public")

    def test_source_attribution_is_structured_data_only(self):
        response = TestClient(create_app("public")).get("/api/v1/status")
        attribution = response.json()["data"]["attribution"]
        self.assertEqual(attribution["provider"], "KKBox")
        self.assertEqual(set(attribution), {"provider", "collection", "source_url", "usage"})
        self.assertNotRegex(response.text, r"(?i)<(?:script|section|html)\b")

    def test_overview_returns_governed_window(self):
        response = TestClient(create_app("private")).get(
            "/api/v1/overview", params={"label_window": "2017-03"}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["eligible_subscribers"], 970960)
        self.assertEqual(payload["meta"]["filters"]["label_window"], "2017-03")

    def test_invalid_window_fails_closed(self):
        response = TestClient(create_app("private")).get(
            "/api/v1/overview", params={"label_window": "latest"}
        )
        self.assertEqual(response.status_code, 422)

    def test_cohorts_never_cross_the_history_cutoff(self):
        client = TestClient(create_app("private"))
        boundaries = {"2017-02": "2017-01-01", "2017-03": "2017-02-01"}
        for window, boundary in boundaries.items():
            with self.subTest(window=window):
                response = client.get(
                    "/api/v1/cohorts", params={"label_window": window, "limit": 240}
                )
                self.assertEqual(response.status_code, 200)
                cohorts = response.json()["data"]
                self.assertTrue(cohorts)
                self.assertLessEqual(
                    max(row["registration_cohort_month"] for row in cohorts), boundary
                )

    def test_exports_are_aggregate_only(self):
        response = TestClient(create_app("public")).get(
            "/api/v1/export/segments.csv", params={"label_window": "2017-03"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("subscriber_token", response.text)

    def test_private_journey_uses_bounded_token(self):
        client = TestClient(create_app("private"))
        listing = client.get("/api/v1/subscribers", params={"limit": 1}).json()
        token = listing["data"][0]["subscriber_token"].lower()
        response = client.get(f"/api/v1/subscribers/{token}")
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.json()["data"]["transactions"]), 24)

    def test_private_scenario_is_aggregate_and_repeat_only(self):
        response = TestClient(create_app("private")).post(
            "/api/v1/scenario",
            json={
                "capacity": 50000,
                "minimum_score": 0.1,
                "contact_cost": 0.5,
                "offer_cost": 2.0,
                "assumed_lift": 0.12,
                "lift_uncertainty": 0.04,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["scope"], "repeat_subscribers_only")
        self.assertEqual(payload["selection"]["eligible_subscribers"], 881701)
        self.assertTrue(payload["selection"]["new_subscribers_excluded"])
        self.assertNotIn("subscriber_token", response.text)

    def test_scenario_invalid_inputs_fail_closed(self):
        client = TestClient(create_app("private"))
        base = {
            "capacity": 50000,
            "minimum_score": 0.1,
            "contact_cost": 0.5,
            "offer_cost": 2.0,
            "assumed_lift": 0.12,
            "lift_uncertainty": 0.04,
        }
        for field, value in (
            ("capacity", 1),
            ("capacity", 50000.5),
            ("minimum_score", 1.1),
            ("contact_cost", -1),
            ("assumed_lift", 2),
        ):
            with self.subTest(field=field):
                response = client.post("/api/v1/scenario", json={**base, field: value})
                self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
