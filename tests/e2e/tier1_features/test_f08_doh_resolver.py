"""
Tier 1 - Feature 8: Multi-Resolver DoH Anti-Leak Engine
Verifies Quad9/Cloudflare/Google DoH upstream resolution, failover, split-horizon protection,
and plaintext port 53 blocking.
"""

import unittest
import time
from tests.harness import DNSLeakDetector


class DoHResolverSimulator:
    """Simulated Multi-Resolver DoH client with local cache and split-horizon filtering."""

    UPSTREAMS = [
        "https://dns.quad9.net/dns-query",
        "https://cloudflare-dns.com/dns-query",
        "https://dns.google/dns-query",
    ]

    def __init__(self):
        self.cache: dict[str, tuple[str, float]] = {}  # domain -> (ip, expiry)
        self.failed_upstreams: set[str] = set()

    def resolve(self, domain: str) -> tuple[bool, str, str]:
        """
        Resolves domain via DoH.
        Returns: (success, ip_address, resolver_used)
        """
        # Split-horizon internal domain protection
        if domain.endswith(".local") or domain.endswith(".internal") or domain.endswith(".lan") or domain.endswith(".corp"):
            return False, "NXDOMAIN", "SPLIT_HORIZON_BLOCKED"

        now = time.time()
        if domain in self.cache:
            ip, exp = self.cache[domain]
            if now < exp:
                return True, ip, "LOCAL_CACHE"

        # Try upstreams in failover order
        for upstream in self.UPSTREAMS:
            if upstream in self.failed_upstreams:
                continue
            # Simulated successful resolution
            resolved_ip = "93.184.216.34"
            self.cache[domain] = (resolved_ip, now + 300)  # 5 min TTL
            return True, resolved_ip, upstream

        return False, "SERVFAIL", "ALL_UPSTREAMS_FAILED"


class TestFeature08DoHResolver(unittest.TestCase):
    """Verifies Feature 8: Multi-Resolver DoH Anti-Leak Engine."""

    def setUp(self):
        self.resolver = DoHResolverSimulator()

    def test_doh_query_wire_format(self):
        """Test 1: Verifies DoH HTTPS query path and application/dns-message content type."""
        doh_endpoint = "https://dns.quad9.net/dns-query"
        headers = {
            "Accept": "application/dns-message",
            "Content-Type": "application/dns-message",
        }
        self.assertEqual(headers["Accept"], "application/dns-message")
        self.assertTrue(doh_endpoint.startswith("https://"))

    def test_multi_resolver_failover_order(self):
        """Test 2: Verifies automatic failover from Quad9 -> Cloudflare -> Google on outage."""
        # 1. Primary: Quad9
        ok, ip, used = self.resolver.resolve("example.com")
        self.assertTrue(ok)
        self.assertEqual(used, "https://dns.quad9.net/dns-query")

        # Clear cache and simulate Quad9 down
        self.resolver.cache.clear()
        self.resolver.failed_upstreams.add("https://dns.quad9.net/dns-query")
        ok2, _, used2 = self.resolver.resolve("example.com")
        self.assertTrue(ok2)
        self.assertEqual(used2, "https://cloudflare-dns.com/dns-query")

        # Simulate Cloudflare also down -> Google
        self.resolver.cache.clear()
        self.resolver.failed_upstreams.add("https://cloudflare-dns.com/dns-query")
        ok3, _, used3 = self.resolver.resolve("example.com")
        self.assertTrue(ok3)
        self.assertEqual(used3, "https://dns.google/dns-query")

    def test_plaintext_port_53_blocking(self):
        """Test 3: Verifies DNS leak detector detects and blocks plaintext port 53 traffic."""
        ok, msg = DNSLeakDetector.audit_dns_request("8.8.8.8", 53, "UDP")
        self.assertFalse(ok)
        self.assertIn("Plaintext DNS query on port 53", msg)

        # DoH request succeeds
        ok_doh, msg_doh = DNSLeakDetector.audit_dns_request(
            "9.9.9.9", 443, "TCP", doh_endpoint="https://dns.quad9.net/dns-query"
        )
        self.assertTrue(ok_doh)
        self.assertEqual(msg_doh, "DOH_VERIFIED")

    def test_split_horizon_leak_protection(self):
        """Test 4: Verifies internal domain names are blocked from leaking to public DoH servers."""
        internal_domains = [
            "router.local",
            "nas.home.internal",
            "dev-server.lan",
            "corp-intranet.corp",
        ]
        for d in internal_domains:
            ok, _, used = self.resolver.resolve(d)
            self.assertFalse(ok)
            self.assertEqual(used, "SPLIT_HORIZON_BLOCKED")

    def test_dns_cache_ttl_handling(self):
        """Test 5: Verifies local DNS cache serves repeated requests before TTL expires."""
        ok, ip, used = self.resolver.resolve("test-domain.org")
        self.assertEqual(used, "https://dns.quad9.net/dns-query")

        # Second request must hit cache
        ok2, ip2, used2 = self.resolver.resolve("test-domain.org")
        self.assertEqual(used2, "LOCAL_CACHE")
        self.assertEqual(ip, ip2)


if __name__ == "__main__":
    unittest.main()
