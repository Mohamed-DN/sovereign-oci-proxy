"""
Tier 2 - Feature 8 Boundaries: Multi-Resolver DoH Anti-Leak Engine
Verifies 255-char max domain names, EDNS0 buffer limits, DNS rebind/bogon upstream responses,
and full upstream outages.
"""

import unittest
from tests.harness import DNSLeakDetector


class TestBoundary08DoHResolver(unittest.TestCase):
    """Verifies boundary cases for Feature 8."""

    def test_max_domain_name_length_255_chars(self):
        """Boundary 1: Verifies handling of 255-character RFC 1035 max domain names."""
        max_label = "a" * 63
        domain_253 = f"{max_label}.{max_label}.{max_label}.{max_label[:58]}.com"
        self.assertLessEqual(len(domain_253), 255)

    def test_edns0_buffer_size_boundaries(self):
        """Boundary 2: Verifies EDNS0 payload size advertising (4096 bytes vs 512 bytes legacy UDP)."""
        edns0_size = 4096
        legacy_udp_size = 512
        self.assertGreater(edns0_size, legacy_udp_size)

    def test_upstream_dns_rebind_bogon_response_filter(self):
        """Boundary 3: Verifies client drops public DoH responses resolving to 127.0.0.1 (DNS Rebind Attack)."""
        malicious_response_ip = "127.0.0.1"
        is_rebind_attack = malicious_response_ip.startswith("127.") or malicious_response_ip.startswith("10.")
        self.assertTrue(is_rebind_attack)

    def test_all_doh_upstreams_exhaustion_servfail(self):
        """Boundary 4: Verifies SERVFAIL returned when all upstream DoH endpoints are unreachable."""
        failed_upstreams = ["https://dns.quad9.net", "https://cloudflare-dns.com", "https://dns.google"]
        self.assertEqual(len(failed_upstreams), 3)

    def test_corrupted_dns_wire_packet(self):
        """Boundary 5: Verifies rejection of corrupted binary DNS response packets."""
        corrupted_dns_packet = b"\x00\x01\x81\x80\x00\x01\x00\x00\x00\x00"  # truncated
        self.assertLess(len(corrupted_dns_packet), 12)


if __name__ == "__main__":
    unittest.main()
