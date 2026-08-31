"""
Tier 3 - Scenario 20: Node-ID Specific Host Routing with Curve25519 Verification (F14 + F16 + F9)
Verifies client routing to an exact Node ID with cryptographic public key pinning.
"""

import unittest
from tests.harness import MockMeshNetwork, DirectFrame


class TestScenario20HostRoutingSpecificPeer(unittest.TestCase):
    """Pairwise Integration: F14 (Host Routing) + F16 (Control Plane) + F9 (Crypto Overlay)."""

    def test_pinned_host_routing_and_encryption(self):
        mesh = MockMeshNetwork()
        target_node_id = "exit-sg-01"
        target_node = mesh.route_by_host_id(target_node_id)
        self.assertIsNotNone(target_node)
        self.assertEqual(target_node.geoip.country_code, "SG")

        # Verify public key registered in Control Plane matches node key
        cp_node = mesh.control_plane.nodes[target_node_id]
        self.assertEqual(cp_node["pubkey"], target_node.pubkey)

        # Send encrypted DirectFrame to verified public key
        frame = DirectFrame(sender_pubkey=target_node.pubkey, payload=b"DIRECT_TO_PINNED_SG_NODE")
        wire = frame.serialize(key=target_node.privkey)
        parsed = DirectFrame.parse(wire, key=target_node.privkey)
        self.assertEqual(parsed.payload, b"DIRECT_TO_PINNED_SG_NODE")


if __name__ == "__main__":
    unittest.main()
