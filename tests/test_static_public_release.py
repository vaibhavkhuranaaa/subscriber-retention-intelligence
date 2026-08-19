import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_KEYS = {
    "subscriber_token",
    "msno",
    "user_id",
    "email",
    "phone",
    "address",
    "age_reported",
    "gender",
    "city_code",
    "registration_method_code",
    "model_score",
}


def keys(value):
    if isinstance(value, dict):
        found = set(value)
        for child in value.values():
            found.update(keys(child))
        return found
    if isinstance(value, list):
        found = set()
        for child in value:
            found.update(keys(child))
        return found
    return set()


class StaticPublicReleaseTests(unittest.TestCase):
    def test_generated_release_is_public_and_aggregate_only(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/build_static_public_release.py"),
                    "--output",
                    str(output),
                    "--release-id",
                    "test-static",
                ],
                cwd=ROOT,
                env=os.environ.copy(),
                check=True,
                capture_output=True,
                text=True,
            )
            snapshot = json.loads((output / "data/public-snapshot.json").read_text())
            self.assertEqual(snapshot["status"]["meta"]["mode"], "public")
            self.assertEqual(snapshot["status"]["meta"]["release_id"], "test-static")
            self.assertFalse(keys(snapshot).intersection(FORBIDDEN_KEYS))
            self.assertEqual(
                sorted(path.name for path in (output / "exports").glob("*.csv")),
                ["retention-overview-2017-02.csv", "retention-overview-2017-03.csv"],
            )

    def test_generated_release_paths_are_ignored(self):
        for path in ("web/public/data/public-snapshot.json", "web/public/exports/control.csv"):
            result = subprocess.run(
                ["git", "check-ignore", "--quiet", path],
                cwd=ROOT,
                check=False,
            )
            self.assertEqual(result.returncode, 0, path)


if __name__ == "__main__":
    unittest.main()
