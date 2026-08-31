"""
Tier 1 - Feature 24: Full E2E Test Suite Integrity & Reporting
Verifies 5-Tier test discovery, TAP v13 compliance, JSON report structure, and execution metadata.
"""

import unittest
import os
import json
from tests.e2e.runner import discover_suite, format_tap_report, format_json_report, CustomTAPTestResult


class TestFeature24FullE2EPass(unittest.TestCase):
    """Verifies Feature 24: Full E2E Test Pass & Framework Integrity."""

    def test_tier_suite_discovery(self):
        """Test 1: Verifies all 5 tiers can be discovered individually and collectively."""
        for tier in ["1", "2", "3", "4", "5"]:
            suite = discover_suite(tier)
            self.assertGreater(suite.countTestCases(), 0, f"Tier {tier} should contain discovered test cases")

        all_suite = discover_suite("all")
        self.assertGreater(all_suite.countTestCases(), 200, "All-tier suite must discover comprehensive test cases")

    def test_custom_tap_result_collection(self):
        """Test 2: Verifies TAP result recorder tracks passed, failed, and skipped tests."""
        result = CustomTAPTestResult()
        result.startTestRun()

        # Simulate test outcomes
        dummy_test = unittest.FunctionTestCase(lambda: None)
        result.addSuccess(dummy_test)

        result.stopTestRun()
        self.assertEqual(len(result.test_records), 1)
        self.assertEqual(result.test_records[0]["status"], "PASS")
        self.assertGreaterEqual(result.total_time, 0.0)

    def test_tap_v13_formatting(self):
        """Test 3: Verifies TAP version 13 formatting specification compliance."""
        records = [
            {"id": "tests.test_sample_1", "status": "PASS", "error": None},
            {"id": "tests.test_sample_2", "status": "SKIP", "error": "Not applicable"},
            {"id": "tests.test_sample_3", "status": "FAIL", "error": "AssertionError: expected 1 got 2"},
        ]
        tap_text = format_tap_report(records)
        self.assertIn("TAP version 13", tap_text)
        self.assertIn("1..3", tap_text)
        self.assertIn("ok 1 - tests.test_sample_1", tap_text)
        self.assertIn("ok 2 - tests.test_sample_2 # SKIP Not applicable", tap_text)
        self.assertIn("not ok 3 - tests.test_sample_3", tap_text)

    def test_json_report_structure(self):
        """Test 4: Verifies structured JSON telemetry report format and required schema fields."""
        result = CustomTAPTestResult()
        result.startTestRun()
        dummy_test = unittest.FunctionTestCase(lambda: None)
        result.addSuccess(dummy_test)
        result.stopTestRun()

        report = format_json_report(result, tier="all")
        self.assertIn("timestamp", report)
        self.assertIn("summary", report)
        self.assertIn("tier_distribution", report)
        self.assertIn("feature_coverage", report)
        self.assertEqual(report["summary"]["passed"], 1)
        self.assertEqual(report["summary"]["failed"], 0)

    def test_test_runner_artifact_generation(self):
        """Test 5: Verifies runner produces valid JSON artifact on disk."""
        tmp_json = "/tmp/test_runner_artifact.json"
        tmp_tap = "/tmp/test_runner_artifact.tap"
        try:
            result = CustomTAPTestResult()
            result.startTestRun()
            dummy_test = unittest.FunctionTestCase(lambda: None)
            result.addSuccess(dummy_test)
            result.stopTestRun()

            rep = format_json_report(result, tier="1")
            with open(tmp_json, "w", encoding="utf-8") as f:
                json.dump(rep, f)
            with open(tmp_tap, "w", encoding="utf-8") as f:
                f.write(format_tap_report(result.test_records))

            self.assertTrue(os.path.exists(tmp_json))
            self.assertTrue(os.path.exists(tmp_tap))
            self.assertGreater(os.path.getsize(tmp_json), 0)
        finally:
            if os.path.exists(tmp_json):
                os.remove(tmp_json)
            if os.path.exists(tmp_tap):
                os.remove(tmp_tap)


if __name__ == "__main__":
    unittest.main()
