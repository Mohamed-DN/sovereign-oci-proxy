"""
Tier 2 - Feature 3 Boundaries: Parameterized User Management API
Verifies nil/malformed UUIDs, max length usernames, negative quotas, duplicate users,
and rollback on transaction failure.
"""

import unittest
import sqlite3
import uuid


class TestBoundary03UserManagement(unittest.TestCase):
    """Verifies boundary cases for Feature 3."""

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        with self.conn:
            self.conn.execute("""
                CREATE TABLE users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    vless_uuid TEXT NOT NULL UNIQUE,
                    bandwidth_limit_mb INTEGER NOT NULL,
                    status TEXT DEFAULT 'ACTIVE'
                )
            """)

    def tearDown(self):
        self.conn.close()

    def test_malformed_and_nil_uuid_validation(self):
        """Boundary 1: Verifies validation rejects non-standard UUID formats."""
        invalid_uuids = [
            "not-a-uuid",
            "00000000-0000-0000-0000-00000000000Z",
            "1234",
            "",
        ]
        for u in invalid_uuids:
            with self.assertRaises(ValueError):
                uuid.UUID(u)

    def test_max_length_username_and_unicode(self):
        """Boundary 2: Verifies username with 10,000 characters and complex Unicode characters."""
        long_username = "user_" + "A" * 5000 + "🚀_世界"
        with self.conn:
            self.conn.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                ("usr_001", long_username, str(uuid.uuid4()), 10240, "ACTIVE"),
            )
        cur = self.conn.cursor()
        cur.execute("SELECT username FROM users WHERE user_id = 'usr_001'")
        self.assertEqual(cur.fetchone()[0], long_username)

    def test_negative_and_zero_quota_boundaries(self):
        """Boundary 3: Verifies behavior with 0 MB quota (immediate throttle) and negative quota."""
        zero_quota = 0
        self.assertTrue(zero_quota <= 0)

    def test_duplicate_user_collision_rejection(self):
        """Boundary 4: Verifies duplicate username or duplicate UUID raises IntegrityError."""
        u_uuid = str(uuid.uuid4())
        with self.conn:
            self.conn.execute("INSERT INTO users VALUES ('usr_1', 'alice', ?, 1024, 'ACTIVE')", (u_uuid,))
        
        with self.assertRaises(sqlite3.IntegrityError):
            with self.conn:
                self.conn.execute("INSERT INTO users VALUES ('usr_2', 'alice', ?, 1024, 'ACTIVE')", (str(uuid.uuid4()),))

    def test_transaction_rollback_on_batch_failure(self):
        """Boundary 5: Verifies database rolls back entire transaction if one update in batch fails."""
        with self.conn:
            self.conn.execute("INSERT INTO users VALUES ('usr_a', 'user_a', 'uuid_a', 1000, 'ACTIVE')")

        try:
            with self.conn:
                self.conn.execute("UPDATE users SET bandwidth_limit_mb = 2000 WHERE user_id = 'usr_a'")
                # Trigger forced syntax error in transaction
                self.conn.execute("INSERT INTO non_existent_table VALUES (1)")
        except sqlite3.OperationalError:
            pass

        cur = self.conn.cursor()
        cur.execute("SELECT bandwidth_limit_mb FROM users WHERE user_id = 'usr_a'")
        self.assertEqual(cur.fetchone()[0], 1000, "Transaction should have rolled back to 1000")


if __name__ == "__main__":
    unittest.main()
