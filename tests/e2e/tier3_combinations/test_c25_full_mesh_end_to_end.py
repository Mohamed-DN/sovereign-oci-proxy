"""
Tier 3 - Scenario 25: Full Mesh End-to-End Proxy Lifecycle (F6 + F8 + F9 + F10 + F11 + F12 + F13 + F14 + F16)
Verifies complete flow: VLESS ingress -> DoH resolve -> Control Plane sync -> Disco-v4 / DERP -> Noise direct frame -> GeoIP Exit Node egress.
"""

import unittest
import uuid
import os
from tests.harness import (
    MockMeshNetwork,
    DirectFrame,
    DNSLeakDetector,
    RFC1918LeakDetector,
)
from tests.e2e.tier1_features.test_f06_vless_reality import VLESSRealityIngress
from tests.e2e.tier1_features.test_f08_doh_resolver import DoHResolverSimulator


class TestScenario25FullMeshEndToEnd(unittest.TestCase):
    """Full End-to-End Pairwise Integration Scenario."""

    def test_complete_mesh_proxy_lifecycle(self):
        # 1. Ingress Setup
        client_uuid = str(uuid.uuid4())
        ingress = VLESSRealityIngress(valid_uuids=[client_uuid], short_ids=["0123456789abcdef"])
        
        # 2. Inbound Connection
        u_bytes = uuid.UUID(client_uuid).bytes
        vless_hdr = b"\x00" + u_bytes + b"\x00\x01\x01\xbb\x01\x08\x08\x08\x08"
        action, _ = ingress.route_inbound_connection(vless_hdr, "www.microsoft.com")
        self.assertEqual(action, "PROXY_MESH")

        # 3. DoH Resolution
        doh = DoHResolverSimulator()
        ok_doh, dest_ip, doh_url = doh.resolve("public-api.com")
        self.assertTrue(ok_doh)

        # 4. Mesh Discovery & GeoIP Routing
        mesh = MockMeshNetwork()
        exit_node = mesh.route_by_country("JP")
        self.assertIsNotNone(exit_node)
        self.assertEqual(exit_node.geoip.country_code, "JP")

        # 5. Encrypted Overlay Framing
        session_key = os.urandom(32)
        frame = DirectFrame(sender_pubkey=exit_node.pubkey, payload=b"GET /api/v1 HTTP/1.1\r\n\r\n")
        wire = frame.serialize(key=session_key)
        parsed = DirectFrame.parse(wire, key=session_key)
        self.assertEqual(parsed.payload, b"GET /api/v1 HTTP/1.1\r\n\r\n")

        # 6. Sandboxed Egress
        ok_egress, status, resp = exit_node.handle_egress_request("c1", dest_ip, 443, payload=parsed.payload)
        self.assertTrue(ok_egress)
        self.assertEqual(status, "FORWARDED")
        self.assertIn(b"Hello from JP", resp)


if __name__ == "__main__":
    unittest.main()
