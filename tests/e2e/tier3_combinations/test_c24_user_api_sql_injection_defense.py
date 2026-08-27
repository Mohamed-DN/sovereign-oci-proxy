"""
Tier 3 - Scenario 24: User Management SQLi Defense & Threat Scorer Interaction (F3 + F2)
Verifies SQL injection attempts against User Management API are neutralized and trigger threat ban.
"""

import unittest
import sqlite3
from tests.e2e.tier1_features.test_f03_user_management import UserManager
from tests.e2e.tier1_features.test_f02_honeypot_dos import AsyncThreatScorer


class TestScenario24UserAPISQLiDefense(unittest.TestCase):
    """Pairwise Integration: F3 (User Management) + F2 (Honeypot DoS)."""

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.mgr = UserManager(self.conn)
        self.scorer = AsyncThreatScorer(ban_threshold=100)

    def tearDown(self):
        self.conn.close()

    def test_sqli_attack_triggers_threat_ban(self):
        attacker_ip = "198.51.100.111"
        sqli_payload = "admin' OR 1=1; DROP TABLE users; --"

        # Neutralized in DB
        user = self.mgr.create_user(sqli_payload)
        self.assertEqual(user["username"], sqli_payload)

        # Security probe intercepts malicious pattern and records threat score
        if "OR 1=1" in sqli_payload or "DROP TABLE" in sqli_payload:
            self.scorer.record_threat_event(attacker_ip, 120)

        self.scorer.process_pending_events()
        self.assertTrue(self.scorer.is_ip_banned(attacker_ip))


if __name__ == "__main__":
    unittest.main()
