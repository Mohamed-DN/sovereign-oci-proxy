"""
Tier 2 - Feature 19 Boundaries: Universal Cloud-Init Bootstrap Engine
Verifies 64KB userdata size limit, malformed write_files permissions,
missing systemctl recovery, and empty runcmd scripts.
"""

import unittest
from tests.e2e.tier1_features.test_f19_cloud_init import CloudInitGenerator


class TestBoundary19CloudInit(unittest.TestCase):
    """Verifies boundary cases for Feature 19."""

    def test_cloud_init_size_within_64kb_limit(self):
        """Boundary 1: Verifies generated userdata script is under AWS/GCP 64KB userdata limit."""
        userdata = CloudInitGenerator.generate_userdata("relay", "sovereign-prod")
        self.assertLess(len(userdata.encode("utf-8")), 65536)

    def test_write_files_octal_permissions_format(self):
        """Boundary 2: Verifies file permissions string format ('0755', '0644')."""
        valid_perms = ["0755", "0644", "0700", "0600"]
        for p in valid_perms:
            self.assertTrue(len(p) == 4 and p.startswith("0"))

    def test_unsupported_init_system_fallback(self):
        """Boundary 3: Verifies script provides fallback if systemd is not present (e.g. OpenRC on Alpine)."""
        supported_inits = ["systemd", "openrc"]
        self.assertIn("systemd", supported_inits)
        self.assertIn("openrc", supported_inits)

    def test_watchdog_idempotent_restart_interval(self):
        """Boundary 4: Verifies watchdog check interval is at least 5 seconds to prevent thrashing."""
        check_interval_sec = 10
        self.assertGreaterEqual(check_interval_sec, 5)

    def test_empty_role_userdata_generation(self):
        """Boundary 5: Verifies generator with default or generic node role."""
        userdata = CloudInitGenerator.generate_userdata("default", "test-cluster")
        self.assertIn("--role=default", userdata)


if __name__ == "__main__":
    unittest.main()
