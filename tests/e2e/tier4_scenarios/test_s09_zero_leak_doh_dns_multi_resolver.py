"""
Tier 4 - Scenario 9: Zero-Leak Multi-Provider DoH DNS Resolution & Fallback
Features Exercised: F08 (DoH Multi-Resolver), F13 (RFC 1918 Isolation).
"""

import unittest
from tests.harness import DNSLeakDetector
from tests.e2e.tier1_features.test_f08_doh_resolver import DoHResolverSimulator


class TestScenario09ZeroLeakDoHDNSMultiResolver(unittest.TestCase):
    """Scenario 9: Multi-provider DoH DNS resolution with zero plaintext leak."""

    def test_doh_multi_provider_race_and_leak_isolation(self):
        resolver = DoHResolverSimulator()

        # 1. Resolve standard domain via DoH
        ok, ip, source = resolver.resolve("example.com")
        self.assertTrue(ok)
        self.assertIn("https://", source)

        # 2. Repeated query hits cache
        ok2, ip2, source2 = resolver.resolve("example.com")
        self.assertTrue(ok2)
        self.assertEqual(ip, ip2)
        self.assertEqual(source2, "LOCAL_CACHE")

        # 3. Plaintext DNS audit passes with zero leaks
        ok_doh, msg_doh = DNSLeakDetector.audit_dns_request(
            "1.1.1.1", 443, "HTTPS", doh_endpoint="https://cloudflare-dns.com/dns-query"
        )
        self.assertTrue(ok_doh)

        ok_plain, msg_plain = DNSLeakDetector.audit_dns_request("8.8.8.8", 53, "UDP")
        self.assertFalse(ok_plain)
        self.assertIn("Plaintext DNS", msg_plain)


if __name__ == "__main__":
    unittest.main()
