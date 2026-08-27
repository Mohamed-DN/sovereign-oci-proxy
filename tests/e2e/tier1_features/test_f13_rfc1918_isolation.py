"""
Tier 1 - Feature 13: RFC 1918 / Bogon Subnet Isolation
Verifies kernel/eBPF/netstack packet filters blocking private IP ranges
(10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, loopback, link-local, multicast, bogons)
and restricted ports (25, 445, 137, 138, 139).
"""

import unittest
from tests.harness import MockClientExitNode, NodeGeoIP, RFC1918LeakDetector


class TestFeature13RFC1918Isolation(unittest.TestCase):
    """Verifies Feature 13: RFC 1918 / Bogon Subnet Isolation."""

    def setUp(self):
        geoip = NodeGeoIP(country_code="DE", city="Frankfurt", latitude=50.1, longitude=8.6)
        self.node = MockClientExitNode(node_id="exit-de-test", geoip=geoip)

    def test_rfc1918_private_ranges_dropped(self):
        """Test 1: Verifies Class A, B, and C private networks are strictly dropped."""
        private_ips = ["10.0.0.1", "10.254.1.1", "172.16.0.1", "172.31.255.1", "192.168.1.1", "192.168.100.1"]
        for ip in private_ips:
            ok, status, _ = self.node.handle_egress_request("c1", ip, 80)
            self.assertFalse(ok, f"Private IP {ip} should be dropped")
            self.assertIn("DROP_RFC1918_BOGON", status)

    def test_loopback_and_link_local_dropped(self):
        """Test 2: Verifies loopback (127.0.0.0/8) and link-local (169.254.0.0/16) are dropped."""
        special_ips = ["127.0.0.1", "127.0.1.1", "169.254.169.254", "169.254.1.1"]
        for ip in special_ips:
            ok, status, _ = self.node.handle_egress_request("c1", ip, 80)
            self.assertFalse(ok, f"Special IP {ip} should be dropped")
            self.assertIn("DROP_RFC1918_BOGON", status)

    def test_multicast_and_reserved_dropped(self):
        """Test 3: Verifies multicast (224.0.0.0/4) and reserved (240.0.0.0/4) are dropped."""
        bogon_ips = ["224.0.0.1", "239.255.255.250", "240.0.0.1", "255.255.255.255"]
        for ip in bogon_ips:
            ok, status, _ = self.node.handle_egress_request("c1", ip, 80)
            self.assertFalse(ok, f"Bogon IP {ip} should be dropped")

    def test_smtp_port_25_spam_block(self):
        """Test 4: Verifies SMTP port 25 is blocked even on public IPs to prevent spam abuse."""
        public_ip = "93.184.216.34"
        ok, status, _ = self.node.handle_egress_request("c1", public_ip, 25)
        self.assertFalse(ok)
        self.assertEqual(status, "DROP_RESTRICTED_PORT_25")

    def test_smb_netbios_ports_block(self):
        """Test 5: Verifies SMB (445) and NetBIOS (137, 138, 139) ports are blocked on egress."""
        public_ip = "93.184.216.34"
        for port in [445, 137, 138, 139]:
            ok, status, _ = self.node.handle_egress_request("c1", public_ip, port)
            self.assertFalse(ok, f"Restricted port {port} should be blocked")
            self.assertEqual(status, f"DROP_RESTRICTED_PORT_{port}")


if __name__ == "__main__":
    unittest.main()
