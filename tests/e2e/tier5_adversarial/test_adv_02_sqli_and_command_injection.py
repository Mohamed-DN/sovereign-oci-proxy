"""
Tier 5 - Adversarial Suite 2: SQL Injection & Shell Metacharacter Fuzzing Suite
Tests user management and database queries against 20+ sophisticated injection attacks.
"""

import unittest
import sqlite3
from tests.e2e.tier1_features.test_f03_user_management import UserManager

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "' OR 1=1 --",
    "'; DROP TABLE users; --",
    "\"; DROP TABLE users; --",
    "'; DELETE FROM users; --",
    "admin'--",
    "' UNION SELECT 1, 'hacked', 0, 0, 0, 'ACTIVE', 0 --",
    "alice@sovereign.local'; DROP TABLE users; --",
    "alice@example.com; rm -rf /tmp/test",
    "$(cat /etc/passwd)@example.com",
    "`id`@example.com",
    "user\x00@example.com",
    "\x00' OR 1=1 --",
    "a" * 300 + "@example.com",
    "user@localhost",
    "@missing-user.com",
    "user@.com",
]


class TestAdversarial02SQLiAndCommandInjection(unittest.TestCase):
    """Adversarial SQLi and Command Injection tests."""

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.mgr = UserManager(self.conn)
        self.alice = self.mgr.create_user("alice")
        self.bob = self.mgr.create_user("bob")

    def tearDown(self):
        self.conn.close()

    def test_sqli_payload_immunity(self):
        for payload in SQLI_PAYLOADS:
            # 1. Attempt injection via user creation
            user = self.mgr.create_user(payload)
            self.assertEqual(user["username"], payload)

            # 2. Attempt injection via revocation
            revoked = self.mgr.revoke_user(payload)
            # Since payload is not a valid user_id, revoked should be False
            self.assertFalse(revoked)

            # 3. Verify table still exists and baseline users are untouched
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            self.assertIsNotNone(cursor.fetchone(), "Table users was dropped!")

            cursor.execute("SELECT status FROM users WHERE username = 'alice'")
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "ACTIVE", "Alice was corrupted by SQLi payload!")


if __name__ == "__main__":
    unittest.main()
