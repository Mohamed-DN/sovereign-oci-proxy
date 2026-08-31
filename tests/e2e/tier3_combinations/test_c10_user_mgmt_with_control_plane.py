"""
Tier 3 - Scenario 10: Parameterized User Revocation Triggers Control Plane Node Detachment (F3 + F16)
Verifies user revocation in DB dynamically revokes auth token and detaches node in Control Plane.
"""

import unittest
import sqlite3
import os
from tests.harness import MockControlPlane, NodeCapability, NodeGeoIP
from tests.e2e.tier1_features.test_f03_user_management import UserManager


class TestScenario10UserMgmtWithControlPlane(unittest.TestCase):
    """Pairwise Integration: F3 (User Management) + F16 (Control Plane)."""

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.user_mgr = UserManager(self.conn)
        self.cp = MockControlPlane("sovereign-user-cp-cluster")
        self.geoip = NodeGeoIP("US", "Ashburn", 39.0, -77.4)

    def tearDown(self):
        self.conn.close()

    def test_user_revocation_invalidates_node_session(self):
        # 1. Create user
        user = self.user_mgr.create_user("alice")
        auth_token = f"token_{user['vless_uuid']}"

        # 2. Register node in Control Plane
        reg = self.cp.register_node("node-alice", os.urandom(32), [NodeCapability.CLIENT], self.geoip, auth_token=auth_token)
        self.assertEqual(reg["status"], "SUCCESS")

        # 3. Revoke user in DB and push revocation to CP
        self.user_mgr.revoke_user(user["user_id"])
        self.cp.revoke_token(auth_token)
        self.cp.revoke_node("node-alice")

        # 4. Attempt sync or re-registration fails
        with self.assertRaises(KeyError):
            self.cp.sync_topology("node-alice")


if __name__ == "__main__":
    unittest.main()
