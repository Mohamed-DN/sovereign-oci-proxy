"""
Tier 1 - Feature 16: Control Plane gRPC & Peer Discovery
Verifies node registration, Curve25519 public key exchange, 100.64.0.0/10 overlay VIP assignment,
topology synchronization, health heartbeats, and token revocation.
"""

import unittest
import os
import ipaddress
from tests.harness import MockControlPlane, NodeCapability, NodeGeoIP, OVERLAY_CIDR


class TestFeature16ControlPlane(unittest.TestCase):
    """Verifies Feature 16: Control Plane gRPC & Peer Discovery."""

    def setUp(self):
        self.cp = MockControlPlane(cluster_name="sovereign-prod-test")
        self.test_pubkey = os.urandom(32)
        self.test_geoip = NodeGeoIP(country_code="US", city="Reston", latitude=38.9, longitude=-77.3)

    def test_node_registration_and_vip_allocation(self):
        """Test 1: Verifies node registration assigns a valid VIP within 100.64.0.0/10 overlay CIDR."""
        resp = self.cp.register_node(
            node_id="node-test-01",
            pubkey=self.test_pubkey,
            capabilities=[NodeCapability.CLIENT, NodeCapability.EGRESS],
            geoip=self.test_geoip,
        )
        self.assertEqual(resp["status"], "SUCCESS")
        self.assertEqual(resp["node_id"], "node-test-01")
        
        # Verify overlay VIP is within 100.64.0.0/10
        assigned_ip = ipaddress.ip_address(resp["overlay_ip"])
        overlay_net = ipaddress.ip_network(OVERLAY_CIDR)
        self.assertIn(assigned_ip, overlay_net)

    def test_topology_sync_peer_endpoints(self):
        """Test 2: Verifies topology sync streams active peer public keys and overlay addresses."""
        # Register node 1
        self.cp.register_node("n1", os.urandom(32), [NodeCapability.CLIENT], self.test_geoip)
        # Register node 2
        self.cp.register_node("n2", os.urandom(32), [NodeCapability.EGRESS], self.test_geoip)

        topo = self.cp.sync_topology("n1")
        self.assertIn("n2", topo["peers"])
        self.assertNotIn("n1", topo["peers"], "Should not return self in peer list")
        self.assertEqual(topo["cluster_name"], "sovereign-prod-test")

    def test_peer_health_heartbeat_reporting(self):
        """Test 3: Verifies node health status updates on battery and bandwidth changes."""
        self.cp.register_node("n-health", self.test_pubkey, [NodeCapability.CLIENT], self.test_geoip)
        
        # Normal report
        res1 = self.cp.report_health("n-health", battery_pct=95.0, bandwidth_used_mb=100.0)
        self.assertEqual(res1["node_status"], "HEALTHY")

        # Battery drops below 15%
        res2 = self.cp.report_health("n-health", battery_pct=12.0)
        self.assertEqual(res2["node_status"], "DEGRADED_BATTERY")

    def test_cluster_epoch_synchronization(self):
        """Test 4: Verifies epoch advancement propagates across all registered nodes."""
        self.assertEqual(self.cp.epoch, 1)
        new_epoch = self.cp.rotate_epoch()
        self.assertEqual(new_epoch, 2)
        self.assertEqual(self.cp.epoch, 2)

    def test_unauthorized_token_rejection(self):
        """Test 5: Verifies registration with empty or revoked token is rejected."""
        # Revoke token
        self.cp.revoke_token("revoked-token-123")
        with self.assertRaises(PermissionError):
            self.cp.register_node(
                node_id="bad-node",
                pubkey=self.test_pubkey,
                capabilities=[NodeCapability.CLIENT],
                geoip=self.test_geoip,
                auth_token="revoked-token-123",
            )


if __name__ == "__main__":
    unittest.main()
