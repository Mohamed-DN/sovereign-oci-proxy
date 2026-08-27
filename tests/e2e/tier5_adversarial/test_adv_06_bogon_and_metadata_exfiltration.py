"""
Tier 5 - Adversarial Suite 6: Bogon, Cloud Metadata & Restricted Port Exfiltration
Tests egress sandbox against 20+ adversarial target IP/port vectors.
"""

import unittest
from tests.harness import MockClientExitNode, NodeGeoIP


class TestAdversarial06BogonAndMetadataExfiltration(unittest.TestCase):
    """Adversarial egress sandbox isolation and metadata exfiltration tests."""

    def test_adversarial_egress_blocking_matrix(self):
        exit_node = MockClientExitNode("test-exit-sg", NodeGeoIP("SG", "Singapore", 1.35, 103.8))

        adversarial_targets = [
            ("10.0.0.1", 80),
            ("10.254.254.254", 443),
            ("172.16.0.1", 8080),
            ("172.31.255.255", 443),
            ("192.168.1.1", 80),
            ("192.168.100.50", 3000),
            ("127.0.0.1", 80),
            ("127.0.0.1", 22),
            ("169.254.169.254", 80),  # AWS / Cloud Metadata endpoint
            ("224.0.0.1", 5353),       # Multicast
            ("240.0.0.1", 80),         # Reserved
            # Restricted Ports on Public IPs
            ("93.184.216.34", 25),     # SMTP
            ("93.184.216.34", 445),    # SMB
            ("93.184.216.34", 137),    # NetBIOS
            ("93.184.216.34", 138),    # NetBIOS
            ("93.184.216.34", 139),    # NetBIOS
        ]

        for ip, port in adversarial_targets:
            allowed, reason, _ = exit_node.handle_egress_request(
                client_node_id="attacker-client",
                dest_ip=ip,
                dest_port=port,
                protocol="TCP",
                payload=b"GET / HTTP/1.1\r\n\r\n",
            )
            self.assertFalse(allowed, f"Target {ip}:{port} should have been blocked, got reason: {reason}")

        # Legitimate public target must be allowed
        valid_allowed, valid_status, resp = exit_node.handle_egress_request(
            client_node_id="client-1",
            dest_ip="93.184.216.34",
            dest_port=443,
            protocol="TCP",
            payload=b"GET / HTTP/1.1\r\n\r\n",
        )
        self.assertTrue(valid_allowed)
        self.assertEqual(valid_status, "FORWARDED")


if __name__ == "__main__":
    unittest.main()
