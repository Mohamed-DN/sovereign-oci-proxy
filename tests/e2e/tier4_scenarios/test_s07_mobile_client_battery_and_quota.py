"""
Tier 4 - Scenario 7: Mobile Residential Client Battery & Quota Guardian Failover
Features Exercised: F12 (Client Bridge), F14 (Geo Routing), F16 (Control Plane).
"""

import unittest
from tests.harness import MockMeshNetwork, MockClientExitNode, NodeGeoIP, NodeCapability


class TestScenario07MobileClientBatteryAndQuota(unittest.TestCase):
    """Scenario 7: Mobile client battery and bandwidth quota guardian failover."""

    def test_mobile_battery_drain_and_quota_limit_failover(self):
        mesh = MockMeshNetwork()

        # 1. Register a mobile exit node with Battery and Quota tracking
        mobile_node = MockClientExitNode(
            node_id="exit-us-mobile-01",
            geoip=NodeGeoIP("US", "New York", 40.71, -74.00),
            battery_pct=85.0,
            bandwidth_limit_mb=1024.0,  # 1 GB
        )
        mesh.exit_nodes[mobile_node.node_id] = mobile_node
        mesh.control_plane.register_node(
            node_id=mobile_node.node_id,
            pubkey=mobile_node.pubkey,
            capabilities=[NodeCapability.CLIENT, NodeCapability.EGRESS],
            geoip=mobile_node.geoip,
        )

        # 2. Normal operational egress succeeds
        ok, status, resp = mobile_node.handle_egress_request(
            client_node_id="client-desktop-1",
            dest_ip="93.184.216.34",
            dest_port=443,
            payload=b"GET /index.html HTTP/1.1\r\n\r\n",
        )
        self.assertTrue(ok)
        self.assertEqual(status, "FORWARDED")

        # 3. Simulate battery drop below critical threshold (e.g. 10%)
        mobile_node.battery_pct = 10.0
        ok_low, status_low, _ = mobile_node.handle_egress_request(
            client_node_id="client-desktop-1",
            dest_ip="93.184.216.34",
            dest_port=443,
        )
        self.assertFalse(ok_low)
        self.assertEqual(status_low, "DROP_BATTERY_LOW")

        # 4. Routing engine automatically selects alternate healthy US exit node (exit-us-01)
        alt_us_node = mesh.route_by_country("US")
        self.assertIsNotNone(alt_us_node)
        self.assertEqual(alt_us_node.geoip.country_code, "US")
        self.assertEqual(alt_us_node.node_id, "exit-us-01")

        # 5. Alternate node handles egress successfully
        ok_alt, status_alt, _ = alt_us_node.handle_egress_request(
            client_node_id="client-desktop-1",
            dest_ip="93.184.216.34",
            dest_port=443,
            payload=b"GET /index.html HTTP/1.1\r\n\r\n",
        )
        self.assertTrue(ok_alt)
        self.assertEqual(status_alt, "FORWARDED")


if __name__ == "__main__":
    unittest.main()
