import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "reconcile_semantics", ROOT / "scripts/reconcile_semantics.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

BUILD_SPEC = importlib.util.spec_from_file_location(
    "build_semantics", ROOT / "scripts/build_semantics.py"
)
BUILD_MODULE = importlib.util.module_from_spec(BUILD_SPEC)
BUILD_SPEC.loader.exec_module(BUILD_MODULE)


class SemanticContractTests(unittest.TestCase):
    def test_relative_error_handles_zero(self):
        self.assertEqual(MODULE.relative_error(0, 0), 0)
        self.assertEqual(MODULE.relative_error(1, 0), 1)

    def test_public_models_exclude_private_fields(self):
        forbidden = {
            "subscriber_token",
            "city_code",
            "age_reported",
            "gender",
            "registration_method_code",
        }
        for path in (ROOT / "models/public").glob("*.sql"):
            self.assertTrue(forbidden.isdisjoint(path.read_text().split()))

    def test_resource_caps_are_declared(self):
        profile = (ROOT / "profiles.yml").read_text()
        self.assertIn("threads: 1", profile)
        self.assertIn("memory_limit: 4GB", profile)

    def test_combined_storage_limit_is_enforced(self):
        BUILD_MODULE.assert_storage(10 * BUILD_MODULE.GIB, BUILD_MODULE.GIB)
        with self.assertRaisesRegex(RuntimeError, "exceed 11 GiB"):
            BUILD_MODULE.assert_storage(10 * BUILD_MODULE.GIB, 2 * BUILD_MODULE.GIB)


if __name__ == "__main__":
    unittest.main()
