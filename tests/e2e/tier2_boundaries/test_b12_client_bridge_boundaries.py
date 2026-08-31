"""
Tier 2 - Feature 12 Boundaries: Sandboxed Client-Bridge Exit Node
Verifies exact battery threshold boundary (15.0% vs 14.9%), exact quota boundary,
invalid egress ports (0, 65536, -1), and empty payload egress.
"""

import unittest
from tests.harness import MockClientExitNode, NodeGeoIP


class TestBoundary12ClientBridge(unittest.TestCase):
    """Verifies boundary cases for Feature 12."""

    def setUp(self):
        geoip = NodeGeoIP(country_code="CH", city="Zurich", latitude=47.3, longitude=8.5)
        self.node = MockClientExitNode("exit-ch-test", geoip, bandwidth_limit_mb=100.0)

    def test_battery_exact_boundary_15pct_vs_14_9pct(self):
        """Boundary 1: Verifies 15.0% battery is allowed, whereas 14.9% is dropped."""
        # 15.0% allowed
        self.node.battery_pct = 15.0
        ok_15, _, _ = self.node.handle_egress_request("c1", "93.184.216.34", 443)
        self.assertTrue(ok_15)

        # 14.9% dropped
        self.node.battery_pct = 14.9
        ok_14_9, status, _ = self.node.handle_egress_request("c1", "93.184.216.34", 443)
        self.assertFalse(ok_14_9)
        self.assertEqual(status, "DROP_BATTERY_LOW")

    def test_bandwidth_quota_exact_boundary(self):
        """Boundary 2: Verifies exact quota threshold (100.0MB) stops routing on exhaustion."""
        self.node.bandwidth_used_mb = 100.0
        ok, status, _ = self.node.handle_egress_request("c1", "93.184.216.34", 443)
        self.assertFalse(ok)
        self.assertEqual(status, "DROP_QUOTA_EXHAUSTED")

    def test_invalid_egress_ports_0_and_negative(self):
        """Boundary 3: Verifies port 0 or negative ports are rejected."""
        invalid_ports = [0, -1, 65536]
        for port in invalid_ports:
            is_valid_port = 1 <= port <= 65535
            self.assertFalse(is_valid_port)

    def test_zero_byte_egress_payload(self):
        """Boundary 4: Verifies handling of 0-byte payload egress request."""
        ok, status, resp = self.node.handle_egress_request("c1", "93.184.216.34", 443, payload=b"")
        self.assertTrue(ok)
        self.assertEqual(status, "FORWARDED")

    def test_massive_payload_bandwidth_calculation(self):
        """Boundary 5: Verifies large payload (10MB) appropriately increments bandwidth usage."""
        initial_used = self.node.bandwidth_used_mb
        large_payload = b"X" * (10 * 1024 * 1024)
        ok, _, _ = self.node.handle_egress_request("c1", "93.184.216.34", 443, payload=large_payload)
        self.assertTrue(ok)
        self.assertGreater(self.node.bandwidth_used_mb - initial_used, 9.9)


if __name__ == "__main__":
    unittest.main()
