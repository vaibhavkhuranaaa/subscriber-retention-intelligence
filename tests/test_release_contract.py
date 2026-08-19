import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReleaseContractTests(unittest.TestCase):
    def test_release_manifest_preserves_cost_and_approval_gates(self):
        manifest = json.loads((ROOT / "release/manifest.json").read_text())
        self.assertEqual(manifest["status"], "public_deployed")
        self.assertEqual(manifest["license"], "MIT")
        self.assertEqual(manifest["permanent_demo"]["recurring_cost_ceiling_usd"], 0)
        self.assertFalse(manifest["permanent_demo"]["request_limit_required_before_publication"])
        self.assertEqual(manifest["permanent_demo"]["request_compute_ceiling"], 0)
        self.assertEqual(manifest["permanent_demo"]["deployment_status"], "deployed")
        self.assertEqual(
            manifest["permanent_demo"]["demo_url"],
            "https://subscriber-retention-intelligence.pages.dev/",
        )
        self.assertEqual(
            manifest["scaled_evidence"]["status"],
            "closed_without_provider_execution",
        )
        self.assertEqual(manifest["scaled_evidence"]["cost_ceiling_usd"], 0)
        self.assertEqual(manifest["scaled_evidence"]["actual_cost_usd"], 0)
        self.assertEqual(manifest["public_mode"], "aggregate_dashboard_plus_row_level_dataset")
        self.assertEqual(manifest["detailed_data"]["status"], "public_deployed")
        self.assertEqual(manifest["detailed_data"]["rows"], 442_211_685)
        self.assertEqual(manifest["detailed_data"]["parquet_files"], 32)
        self.assertEqual(manifest["detailed_data"]["compressed_bytes"], 7_522_254_856)
        self.assertEqual(manifest["detailed_data"]["dataset_viewer_configs"], 4)
        self.assertEqual(manifest["detailed_data"]["recurring_cost_ceiling_usd"], 0)
        self.assertFalse(manifest["detailed_data"]["private_salt_published"])
        self.assertIn("MIT License", (ROOT / "LICENSE").read_text())

    def test_public_portfolio_contract_is_zero_cost_and_sha_verified(self):
        project = json.loads((ROOT / "portfolio/project.json").read_text())
        release = json.loads((ROOT / "portfolio/release.json").read_text())
        self.assertEqual(project["version"], 2)
        self.assertEqual(project["slug"], "subscriber-retention-intelligence")
        self.assertEqual(project["deployment"]["status"], "live")
        self.assertTrue(release["publicProject"])
        self.assertFalse(release["paidResource"])
        self.assertFalse(release["costApprovalRequired"])
        self.assertEqual(
            release["verification"]["url"],
            "https://subscriber-retention-intelligence.pages.dev/health.json",
        )
        self.assertEqual(release["verification"]["sourceShaField"], "source_sha")

    def test_public_tree_excludes_private_delivery_data(self):
        candidates = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        existing = [path for path in candidates if (ROOT / path).is_file()]
        forbidden = (
            ".project/",
            ".delivery/",
            "data/private/",
        )
        self.assertFalse(
            [
                path
                for path in existing
                if path.endswith(forbidden[:2]) or path.startswith(forbidden[2:])
            ]
        )

    def test_public_copy_has_no_em_dash_or_private_delivery_path(self):
        paths = [
            ROOT / "README.md",
            ROOT / "PROJECT.md",
            *sorted((ROOT / "docs").rglob("*.md")),
        ]
        for path in paths:
            text = path.read_text()
            self.assertNotIn("—", text, path)
            self.assertNotIn(".delivery/", text, path)

    def test_ci_covers_backend_browser_build_and_lint(self):
        workflow = (ROOT / ".github/workflows/quality.yml").read_text()
        for required in (
            "python -m unittest",
            "dbt parse",
            "verify_power_bi_contract.py",
            "npm run lint",
            "npm run build",
            "npm test",
        ):
            self.assertIn(required, workflow)


if __name__ == "__main__":
    unittest.main()
