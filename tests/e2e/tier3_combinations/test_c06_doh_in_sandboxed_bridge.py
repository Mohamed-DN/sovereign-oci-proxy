"""
Tier 3 - Scenario 6: Remote DoH Resolution in Sandboxed Bridge (F8 + F12 + F13)
Verifies DNS queries originating from client bridge are routed via remote DoH,
preventing plaintext leakage or split-horizon leaks.
"""

import unittest
from tests.harness import MockClientExitNode, NodeGeoIP, DNSLeakDetector
from tests.e2e.tier1_features.test_f08_doh_resolver import DoHResolverSimulator


class TestScenario06DoHInSandboxedBridge(unittest.TestCase):
    """Pairwise Integration: F8 (DoH Resolver) + F12 (Client Bridge) + F13 (RFC 1918 Isolation)."""

    def test_remote_doh_resolution_inside_egress_bridge(self):
        geoip = NodeGeoIP("SG", "Singapore", 1.35, 103.8)
        node = MockClientExitNode("exit-sg-doh", geoip)
        resolver = DoHResolverSimulator()

        # Step 1: Resolve domain through DoH
        ok_resolve, ip, upstream = resolver.resolve("target-service.com")
        self.assertTrue(ok_resolve)
        self.assertEqual(upstream, "https://dns.quad9.net/dns-query")

        # Step 2: Audit no plaintext DNS
        ok_audit, _ = DNSLeakDetector.audit_dns_request(ip, 443, "TCP", doh_endpoint=upstream)
        self.assertTrue(ok_audit)

        # Step 3: Handle egress via client bridge
        ok_egress, status, resp = node.handle_egress_request("c1", ip, 443, payload=b"GET / HTTP/1.1\r\n\r\n")
        self.assertTrue(ok_egress)
        self.assertIn(b"Hello from SG", resp)


if __name__ == "__main__":
    unittest.main()
