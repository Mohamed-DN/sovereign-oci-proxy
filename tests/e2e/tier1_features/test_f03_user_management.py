"""
Tier 1 - Feature 3: Parameterized User Management API
Verifies parameterized SQLite/SQL queries eliminating SQL injection in user management/revocation.
"""

import unittest
import sqlite3
import uuid
import time


class UserManager:
    """Simulated parameterized User Management Service."""

    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    vless_uuid TEXT NOT NULL UNIQUE,
                    bandwidth_limit_mb INTEGER NOT NULL,
                    bandwidth_used_mb REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'ACTIVE',
                    created_at REAL NOT NULL
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS active_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    started_at REAL NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

    def create_user(self, username: str, quota_mb: int = 10240) -> dict:
        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        vless_uuid = str(uuid.uuid4())
        now = time.time()
        with self.conn:
            self.conn.execute(
                "INSERT INTO users (user_id, username, vless_uuid, bandwidth_limit_mb, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, vless_uuid, quota_mb, now),
            )
        return {"user_id": user_id, "username": username, "vless_uuid": vless_uuid, "status": "ACTIVE"}

    def get_user_by_uuid(self, vless_uuid: str) -> dict | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id, username, vless_uuid, status FROM users WHERE vless_uuid = ?", (vless_uuid,))
        row = cursor.fetchone()
        if row:
            return {"user_id": row[0], "username": row[1], "vless_uuid": row[2], "status": row[3]}
        return None

    def revoke_user(self, user_id: str) -> bool:
        with self.conn:
            # Atomic revocation: update status & remove active sessions
            cur = self.conn.execute("UPDATE users SET status = 'REVOKED' WHERE user_id = ?", (user_id,))
            self.conn.execute("DELETE FROM active_sessions WHERE user_id = ?", (user_id,))
            return cur.rowcount > 0

    def update_quotas_batch(self, updates: list[tuple[str, float]]) -> bool:
        with self.conn:
            self.conn.executemany(
                "UPDATE users SET bandwidth_used_mb = bandwidth_used_mb + ? WHERE user_id = ?",
                [(mb, uid) for uid, mb in updates],
            )
            return True


class TestFeature03UserManagement(unittest.TestCase):
    """Verifies Feature 3: Parameterized User Management API."""

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.mgr = UserManager(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_user_creation_with_parameterized_sql(self):
        """Test 1: Verifies valid user creation with proper UUID and parameterized insertion."""
        user = self.mgr.create_user("alice", 51200)
        self.assertEqual(user["username"], "alice")
        self.assertTrue(len(user["vless_uuid"]) == 36)
        
        fetched = self.mgr.get_user_by_uuid(user["vless_uuid"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["status"], "ACTIVE")

    def test_user_revocation_prepared_statement(self):
        """Test 2: Verifies user revocation updates status and returns true."""
        user = self.mgr.create_user("bob")
        success = self.mgr.revoke_user(user["user_id"])
        self.assertTrue(success)

        fetched = self.mgr.get_user_by_uuid(user["vless_uuid"])
        self.assertEqual(fetched["status"], "REVOKED")

    def test_sqli_immunity_in_username_and_uuid(self):
        """Test 3: Verifies SQL injection payloads are neutralized and treated as literal values."""
        sqli_usernames = [
            "admin' OR '1'='1",
            "bob'; DROP TABLE users; --",
            "carol' UNION SELECT * FROM users --",
        ]
        for uname in sqli_usernames:
            user = self.mgr.create_user(uname)
            # Verify table still exists and literal name stored
            fetched = self.mgr.get_user_by_uuid(user["vless_uuid"])
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["username"], uname)

    def test_transactional_quota_updates(self):
        """Test 4: Verifies batch quota updates operate atomically within a transaction."""
        u1 = self.mgr.create_user("user1")
        u2 = self.mgr.create_user("user2")

        updates = [(u1["user_id"], 150.5), (u2["user_id"], 230.0)]
        self.mgr.update_quotas_batch(updates)

        cursor = self.conn.cursor()
        cursor.execute("SELECT user_id, bandwidth_used_mb FROM users WHERE user_id IN (?, ?)", (u1["user_id"], u2["user_id"]))
        rows = dict(cursor.fetchall())
        self.assertAlmostEqual(rows[u1["user_id"]], 150.5)
        self.assertAlmostEqual(rows[u2["user_id"]], 230.0)

    def test_active_session_revocation_on_deletion(self):
        """Test 5: Verifies active sessions are purged when user is revoked."""
        user = self.mgr.create_user("charlie")
        with self.conn:
            self.conn.execute("INSERT INTO active_sessions VALUES (?, ?, ?)", ("sess_01", user["user_id"], time.time()))

        # Revoke user
        self.mgr.revoke_user(user["user_id"])
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM active_sessions WHERE user_id = ?", (user["user_id"],))
        self.assertEqual(cursor.fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
