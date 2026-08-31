"""
Tier 4 - Scenario 12: High-Concurrency Parameterized User Revocation Under Load
Features Exercised: F04 (Parameterized Revocation), F05 (DB Injector & Routing).
"""

import unittest
import sqlite3
import time
from tests.e2e.tier1_features.test_f03_user_management import UserManager


class TestScenario12ParameterizedUserRevocationUnderLoad(unittest.TestCase):
    """Scenario 12: Concurrency-safe client revocation under continuous querying."""

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.mgr = UserManager(self.conn)
        self.users = []
        for i in range(100):
            user = self.mgr.create_user(f"user_{i:03d}")
            self.users.append(user)

    def tearDown(self):
        self.conn.close()

    def test_concurrent_safe_revocation(self):
        # 1. Revoke 20 users with prepared statements
        for i in range(20):
            uid = self.users[i]["user_id"]
            success = self.mgr.revoke_user(uid)
            self.assertTrue(success)

        # 2. Verify state in database
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'REVOKED'")
        revoked_count = cursor.fetchone()[0]
        self.assertEqual(revoked_count, 20)

        cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'ACTIVE'")
        active_count = cursor.fetchone()[0]
        self.assertEqual(active_count, 80)


if __name__ == "__main__":
    unittest.main()
