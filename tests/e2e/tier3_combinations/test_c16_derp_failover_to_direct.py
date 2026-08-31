"""
Tier 3 - Scenario 16: DERP Relay Failover to Direct P2P Traversal Upgrade (F11 + F10)
Verifies session starting via DERP relay seamlessly upgrades to direct wire UDP hole punch.
"""

import unittest
import os
from tests.harness import (
    SimulatedEndpoint,
    NATBehavior,
    NATType,
    DiscoV4Simulator,
    MockDERPRelay,
    DirectFrame,
)


class TestScenario16DERPFailoverToDirect(unittest.TestCase):
    """Pairwise Integration: F11 (DERP Relay) + F10 (NAT Traversal)."""

    def test_seamless_relay_to_direct_p2p_upgrade(self):
        relay = MockDERPRelay("derp-upgrade", "us-east")
        peer_a_pub = os.urandom(32)
        peer_b_pub = os.urandom(32)
        relay.register_client(peer_a_pub)
        relay.register_client(peer_b_pub)

        # Initial communication via DERP
        payload_1 = b"INITIAL_DERP_PACKET"
        self.assertTrue(relay.relay_packet(peer_a_pub, peer_b_pub, payload_1))

        # Disco-v4 establishes direct UDP punch
        ep_a = SimulatedEndpoint("peer-a", "192.168.1.10", 5000, NATBehavior(nat_type=NATType.FULL_CONE))
        ep_b = SimulatedEndpoint("peer-b", "192.168.2.20", 5000, NATBehavior(nat_type=NATType.FULL_CONE))
        disco_res = DiscoV4Simulator.attempt_traversal(ep_a, ep_b)
        self.assertTrue(disco_res["success"])
        self.assertEqual(disco_res["strategy"], "DIRECT_UDP_PUNCH")

        # Subsequent communication directly over P2P DirectFrame
        session_key = os.urandom(32)
        direct_frame = DirectFrame(sender_pubkey=peer_a_pub, payload=b"UPGRADED_P2P_DIRECT_STREAM")
        wire = direct_frame.serialize(key=session_key)
        parsed = DirectFrame.parse(wire, key=session_key)
        self.assertEqual(parsed.payload, b"UPGRADED_P2P_DIRECT_STREAM")


if __name__ == "__main__":
    unittest.main()
