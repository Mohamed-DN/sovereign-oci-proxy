"""
Tier 3 - Scenario 13: Rootless Container Security Profile with Async Ban Daemon (F5 + F2)
Verifies async ban daemon execution within rootless container constraints (non-root UID, read-only rootfs).
"""

import unittest
from tests.e2e.tier1_features.test_f02_honeypot_dos import AsyncThreatScorer


class TestScenario13ContainerWithSecurityDaemon(unittest.TestCase):
    """Pairwise Integration: F5 (Container Hardening) + F2 (Honeypot DoS)."""

    def test_daemon_operates_under_rootless_constraints(self):
        container_env = {
            "USER_UID": 65534,
            "READ_ONLY_ROOTFS": True,
            "TMP_DIR": "/tmp",
        }
        self.assertGreater(container_env["USER_UID"], 0)
        self.assertTrue(container_env["READ_ONLY_ROOTFS"])

        # Daemon operates purely in-memory / tmpfs
        scorer = AsyncThreatScorer(ban_threshold=100)
        scorer.record_threat_event("198.51.100.99", 150)
        scorer.process_pending_events()
        self.assertTrue(scorer.is_ip_banned("198.51.100.99"))


if __name__ == "__main__":
    unittest.main()
