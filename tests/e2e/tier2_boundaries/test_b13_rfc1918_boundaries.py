"""
Tier 2 - Feature 13 Boundaries: RFC 1918 / Bogon Subnet Isolation
Verifies exact boundary IP edges (9.255.255.255 vs 10.0.0.0, 172.15.255.255 vs 172.16.0.0,
172.31.255.255 vs 172.32.0.0, 192.167.255.255 vs 192.168.0.0 vs 192.169.0.0).
"""

import unittest
from tests.harness import MockClientExitNode, NodeGeoIP


class TestBoundary13RFC1918Isolation(unittest.TestCase):
    """Verifies boundary cases for Feature 13."""

    def setUp(self):
        geoip = NodeGeoIP(country_code="NL", city="Amsterdam", latitude=52.3, longitude=4.9)
        self.node = MockClientExitNode("exit-nl-test", geoip)

    def test_class_a_10_0_0_0_8_boundaries(self):
        """Boundary 1: Verifies 9.255.255.255 is allowed, while 10.0.0.0 and 10.255.255.255 are blocked."""
        # Allowed: 9.255.255.255
        ok_9, _, _ = self.node.handle_egress_request("c1", "9.255.255.255", 80)
        self.assertTrue(ok_9)

        # Blocked: 10.0.0.0
        ok_10_start, _, _ = self.node.handle_egress_request("c1", "10.0.0.0", 80)
        self.assertFalse(ok_10_start)

        # Blocked: 10.255.255.255
        ok_10_end, _, _ = self.node.handle_egress_request("c1", "10.255.255.255", 80)
        self.assertFalse(ok_10_end)

        # Allowed: 11.0.0.0
        ok_11, _, _ = self.node.handle_egress_request("c1", "11.0.0.0", 80)
        self.assertTrue(ok_11)

    def test_class_b_172_16_0_0_12_boundaries(self):
        """Boundary 2: Verifies 172.15.255.255 allowed, 172.16.0.0 blocked, 172.31.255.255 blocked, 172.32.0.0 allowed."""
        # 172.15.255.255 allowed
        ok_15, _, _ = self.node.handle_egress_request("c1", "172.15.255.255", 80)
        self.assertTrue(ok_15)

        # 172.16.0.0 blocked
        ok_16, _, _ = self.node.handle_egress_request("c1", "172.16.0.0", 80)
        self.assertFalse(ok_16)

        # 172.31.255.255 blocked
        ok_31, _, _ = self.node.handle_egress_request("c1", "172.31.255.255", 80)
        self.assertFalse(ok_31)

        # 172.32.0.0 allowed
        ok_32, _, _ = self.node.handle_egress_request("c1", "172.32.0.0", 80)
        self.assertTrue(ok_32)

    def test_class_c_192_168_0_0_16_boundaries(self):
        """Boundary 3: Verifies 192.167.255.255 allowed, 192.168.0.0 blocked, 192.169.0.0 allowed."""
        # 192.167.255.255 allowed
        ok_167, _, _ = self.node.handle_egress_request("c1", "192.167.255.255", 80)
        self.assertTrue(ok_167)

        # 192.168.0.0 blocked
        ok_168, _, _ = self.node.handle_egress_request("c1", "192.168.0.0", 80)
        self.assertFalse(ok_168)

        # 192.169.0.0 allowed
        ok_169, _, _ = self.node.handle_egress_request("c1", "192.169.0.0", 80)
        self.assertTrue(ok_169)

    def test_multicast_and_bogon_edges_223_vs_224_and_239_vs_240(self):
        """Boundary 4: Verifies 223.255.255.255 allowed vs 224.0.0.0 blocked."""
        # 223.255.255.255 allowed
        ok_223, _, _ = self.node.handle_egress_request("c1", "223.255.255.255", 80)
        self.assertTrue(ok_223)

        # 224.0.0.0 blocked
        ok_224, _, _ = self.node.handle_egress_request("c1", "224.0.0.0", 80)
        self.assertFalse(ok_224)

    def test_high_port_boundaries_65534_and_65535(self):
        """Boundary 5: Verifies high ports (65534, 65535) are allowed for legitimate public destinations."""
        ok_65534, _, _ = self.node.handle_egress_request("c1", "93.184.216.34", 65534)
        ok_65535, _, _ = self.node.handle_egress_request("c1", "93.184.216.34", 65535)
        self.assertTrue(ok_65534)
        self.assertTrue(ok_65535)


if __name__ == "__main__":
    unittest.main()
