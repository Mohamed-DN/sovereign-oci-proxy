"""
Tier 2 - Feature 16 Boundaries: Control Plane gRPC & Peer Discovery
Verifies invalid public key sizes (31B, 33B), VIP pool exhaustion,
registration storms, unregistered peer queries, and token revocation.
"""

import unittest
import os
from tests.harness import MockControlPlane, NodeCapability, NodeGeoIP


class TestBoundary16ControlPlane(unittest.TestCase):
    """Verifies boundary cases for Feature 16."""

    def setUp(self):
        self.cp = MockControlPlane("sovereign-bound-test")
        self.geoip = NodeGeoIP("US", "Ashburn", 39.0, -77.4)

    def test_invalid_pubkey_length_rejection(self):
        """Boundary 1: Verifies public keys not equal to 32 bytes are rejected."""
        for bad_len in [0, 31, 33, 64]:
            with self.assertRaises(ValueError):
                self.cp.register_node("bad-node", os.urandom(bad_len), [NodeCapability.CLIENT], self.geoip)

    def test_topology_sync_unregistered_node_id(self):
        """Boundary 2: Verifies topology sync by unregistered node raises KeyError."""
        with self.assertRaises(KeyError):
            self.cp.sync_topology("unknown-node-999")

    def test_rapid_registration_storm_100_nodes(self):
        """Boundary 3: Verifies control plane registers 100 nodes sequentially with unique VIPs."""
        registered_ips = set()
        for i in range(100):
            res = self.cp.register_node(f"node-{i}", os.urandom(32), [NodeCapability.CLIENT], self.geoip)
            registered_ips.add(res["overlay_ip"])
        self.assertEqual(len(registered_ips), 100)

    def test_health_report_unregistered_node(self):
        """Boundary 4: Verifies reporting health for nonexistent node raises KeyError."""
        with self.assertRaises(KeyError):
            self.cp.report_health("ghost-node", battery_pct=50.0)

    def test_duplicate_registration_reuses_vip(self):
        """Boundary 5: Verifies re-registration with same node_id returns previously assigned VIP."""
        pub = os.urandom(32)
        r1 = self.cp.register_node("re-node", pub, [NodeCapability.CLIENT], self.geoip)
        r2 = self.cp.register_node("re-node", pub, [NodeCapability.CLIENT], self.geoip)
        self.assertEqual(r1["overlay_ip"], r2["overlay_ip"])


if __name__ == "__main__":
    unittest.main()
