"""
Tier 3 - Scenario 19: DPI Active Probing Mimicry against Nginx Decoy (F6 + F7)
Verifies that when a state-level DPI scanner probes port 443 with arbitrary TLS handshakes,
the connection is transparently handed over to the hardened Nginx decoy server.
"""

import unittest
from tests.e2e.tier1_features.test_f06_vless_reality import VLESSRealityIngress
from tests.e2e.tier1_features.test_f07_nginx_decoy import DecoyServerSimulator


class TestScenario19DecoyDPIMimicry(unittest.TestCase):
    """Pairwise Integration: F6 (VLESS REALITY) + F7 (Nginx Decoy)."""

    def test_dpi_probe_falls_back_to_hardened_decoy(self):
        ingress = VLESSRealityIngress(valid_uuids=["a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"], short_ids=["0123456789abcdef"])
        decoy = DecoyServerSimulator()

        # 1. State-level DPI scanner sends arbitrary TLS ClientHello / probe
        dpi_probe_header = b"\x16\x03\x01\x00\xfa\x01\x00\x00\xf6\x03\x03" + b"RANDOM_DPI_SCANNER_PROBE"
        action, target = ingress.route_inbound_connection(dpi_probe_header, "www.microsoft.com")
        self.assertEqual(action, "FALLBACK_DECOY")
        self.assertEqual(target, "127.0.0.1:8080")

        # 2. Decoy handles probe with enterprise headers
        status, headers, body = decoy.handle_http_request("/", {"User-Agent": "Mozilla/5.0"})
        self.assertEqual(status, 200)
        self.assertEqual(headers["X-Frame-Options"], "DENY")


if __name__ == "__main__":
    unittest.main()
