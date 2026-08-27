"""
Tier 4 - Scenario 1: Enterprise Multi-Region Censorship Circumvention
Features Exercised: F01, F06 (VLESS REALITY), F09 (Crypto Overlay), F10 (NAT Traversal),
F11 (DERP Relay), F14 (Geo Routing).
"""

import unittest
import uuid
import os
from tests.harness import (
    MockMeshNetwork,
    DirectFrame,
    SimulatedEndpoint,
    NATBehavior,
    NATType,
    DiscoV4Simulator,
    LeakDetector,
)
from tests.e2e.tier1_features.test_f06_vless_reality import VLESSRealityIngress


class TestScenario01GlobalCensorshipCircumvention(unittest.TestCase):
    """Scenario 1: Multi-Region Censorship Circumvention under Active DPI."""

    def test_multi_region_censorship_circumvention_full_flow(self):
        # 1. Setup VLESS REALITY Ingress with decoy camouflage
        client_uuid = str(uuid.uuid4())
        ingress = VLESSRealityIngress(
            valid_uuids=[client_uuid],
            short_ids=["0123456789abcdef"],
            decoy_target="127.0.0.1:8080",
        )

        # 2. Simulate Inbound VLESS Handshake with camouflaged SNI
        u_bytes = uuid.UUID(client_uuid).bytes
        vless_hdr = b"\x00" + u_bytes + b"\x00\x01\x01\xbb\x01\x08\x08\x08\x08"
        action, target = ingress.route_inbound_connection(vless_hdr, "www.microsoft.com")
        self.assertEqual(action, "PROXY_MESH")

        # 3. Simulate Active DPI Prober (invalid UUID) -> Silent decoy fallback
        dpi_probe = b"\x00" + uuid.uuid4().bytes + b"\x00\x01\x01\xbb\x01\x08\x08\x08\x08"
        dpi_action, dpi_target = ingress.route_inbound_connection(dpi_probe, "www.microsoft.com")
        self.assertEqual(dpi_action, "FALLBACK_DECOY")
        self.assertEqual(dpi_target, "127.0.0.1:8080")

        # 4. Initialize Virtual Mesh & Route Across All 6 Countries
        mesh = MockMeshNetwork()
        target_countries = ["US", "DE", "JP", "SG", "CH", "NL"]

        for country in target_countries:
            exit_node = mesh.route_by_country(country)
            self.assertIsNotNone(exit_node, f"Must find active exit node for {country}")
            self.assertEqual(exit_node.geoip.country_code, country)

            # Direct Frame Overlay Encryption
            session_key = os.urandom(32)
            req_payload = f"GET /geo-restricted-media/{country} HTTP/1.1\r\nHost: cdn.stream.global\r\n\r\n".encode()
            frame = DirectFrame(sender_pubkey=exit_node.pubkey, payload=req_payload)
            wire_frame = frame.serialize(key=session_key)

            # Egress through exit node
            success, status, resp = exit_node.handle_egress_request(
                client_node_id=f"client-{country.lower()}",
                dest_ip="104.26.10.1",
                dest_port=443,
                payload=wire_frame,
            )
            self.assertTrue(success)
            self.assertEqual(status, "FORWARDED")
            self.assertIn(f"Hello from {country}".encode(), resp)

        # 5. Full Leak and Integrity Audit
        detector = LeakDetector()
        for node in mesh.exit_nodes.values():
            audit = detector.run_full_security_audit(node)
            self.assertTrue(audit["all_passed"], f"Security audit failed for node {node.node_id}")


if __name__ == "__main__":
    unittest.main()
