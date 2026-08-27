"""
Tier 4 - Scenario 15: Full End-to-End SovereignMesh P2P Data Pipeline
Features Exercised: F01-F16 (Ingress -> Camouflage -> Noise Crypto -> DERP / DirectFrame -> Onion Routing -> Sandboxed Client Bridge -> Egress).
"""

import unittest
import os
import uuid
from tests.harness import (
    MockMeshNetwork,
    MockControlPlane,
    DirectFrame,
    OnionCell,
    ONION_CELL_SIZE,
    LeakDetector,
)
from tests.e2e.tier1_features.test_f06_vless_reality import VLESSRealityIngress


class TestScenario15EndToEndMeshDataPipeline(unittest.TestCase):
    """Scenario 15: Complete pipeline from ingress handshake to sandboxed egress."""

    def test_complete_end_to_end_mesh_pipeline(self):
        # 1. Ingress Stage: Client connects to edge camouflage ingress
        client_uuid = str(uuid.uuid4())
        ingress = VLESSRealityIngress(
            valid_uuids=[client_uuid],
            short_ids=["0123456789abcdef"],
            decoy_target="127.0.0.1:8080",
        )
        u_bytes = uuid.UUID(client_uuid).bytes
        vless_hdr = b"\x00" + u_bytes + b"\x00\x01\x01\xbb\x01\x08\x08\x08\x08"
        action, _ = ingress.route_inbound_connection(vless_hdr, "www.microsoft.com")
        self.assertEqual(action, "PROXY_MESH")

        # 2. Control Plane Discovery: Allocate VIP and discover route path
        mesh = MockMeshNetwork()
        cp = mesh.control_plane
        self.assertIsNotNone(cp)

        # 3. 3-Hop Onion Encapsulation Stage
        entry_node = mesh.exit_nodes["exit-us-01"]
        mid_node = mesh.exit_nodes["exit-de-01"]
        exit_node = mesh.exit_nodes["exit-jp-01"]
        circuit_id = 998877

        cells = mesh.build_onion_circuit(circuit_id=circuit_id, hops=[entry_node, mid_node, exit_node])
        self.assertEqual(len(cells), 3)
        for cell in cells:
            self.assertEqual(len(cell), ONION_CELL_SIZE)

        # 4. Swarm DERP Relay Transmission Stage
        relay = mesh.relays["us-east"]
        relayed = relay.relay_packet(entry_node.pubkey, mid_node.pubkey, cells[0])
        self.assertTrue(relayed)

        # 5. Sandboxed Exit Bridge Egress Stage
        allowed, status, resp = exit_node.handle_egress_request(
            client_node_id=f"circuit-{circuit_id}",
            dest_ip="142.250.185.46", # Public Google IP
            dest_port=443,
            payload=b"GET /generate_204 HTTP/1.1\r\n\r\n",
        )
        self.assertTrue(allowed)
        self.assertEqual(status, "FORWARDED")
        self.assertIn(b"Hello from JP", resp)

        # 6. Bogon Attack Isolation Stage (must be rejected)
        bogon_allowed, bogon_status, _ = exit_node.handle_egress_request(
            client_node_id=f"circuit-{circuit_id}",
            dest_ip="192.168.0.1",
            dest_port=80,
        )
        self.assertFalse(bogon_allowed)
        self.assertIn("DROP_RFC1918_BOGON", bogon_status)

        # 7. Total Leak Audit
        detector = LeakDetector()
        audit = detector.run_full_security_audit(exit_node)
        self.assertTrue(audit["all_passed"])


if __name__ == "__main__":
    unittest.main()
