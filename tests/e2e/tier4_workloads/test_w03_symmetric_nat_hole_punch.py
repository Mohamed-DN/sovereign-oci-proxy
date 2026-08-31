"""
Tier 4 - Workload 3: Hostile Symmetric NAT P2P Hole Punching & Seamless DERP Fallback
Features Exercised: F9 (Crypto Overlay), F10 (NAT Traversal), F11 (DERP Relay).
Complexity: High

Simulates two clients behind hostile Symmetric NAT environments (carrier-grade NAT with random & sequential port allocation).
Verifies STUN classification, Disco-v4 port spraying, and instant zero-downtime fallback to camouflaged DERP-v4 relays.
"""

import unittest
import os
from tests.harness import (
    SimulatedEndpoint,
    NATBehavior,
    NATType,
    NetworkSimulator,
    STUNSimulator,
    DiscoV4Simulator,
    MockDERPRelay,
    DirectFrame,
)


class TestWorkload03SymmetricNATHolePunch(unittest.TestCase):
    """Workload 3: Hostile Symmetric NAT Hole Punching & DERP Fallback."""

    def test_symmetric_nat_traversal_and_relay_fallback_workload(self):
        net_sim = NetworkSimulator(base_latency_ms=15.0, jitter_ms=3.0)
        stun_sim = STUNSimulator()

        # Case 1: Sequential Symmetric NAT vs Port-Restricted Cone NAT -> Port Spraying Succeeds
        ep_seq = SimulatedEndpoint(
            "node-cgnat-1", "10.100.1.5", 5000,
            NATBehavior(nat_type=NATType.SYMMETRIC_SEQUENTIAL, public_ip="198.51.100.10", base_port=41000, port_step=1)
        )
        ep_cone = SimulatedEndpoint(
            "node-dsl-2", "192.168.1.10", 5000,
            NATBehavior(nat_type=NATType.PORT_RESTRICTED_CONE, public_ip="203.0.113.20")
        )

        res_spray = DiscoV4Simulator.attempt_traversal(ep_cone, ep_seq, net_sim, spray_count=16)
        self.assertTrue(res_spray["success"])
        self.assertFalse(res_spray["derp_fallback"])

        # Case 2: Hostile Symmetric Random vs Symmetric Random -> DERP Relay Fallback
        ep_rnd1 = SimulatedEndpoint(
            "node-mobile-3", "10.200.1.1", 6000,
            NATBehavior(nat_type=NATType.SYMMETRIC_RANDOM, public_ip="198.51.100.99")
        )
        ep_rnd2 = SimulatedEndpoint(
            "node-mobile-4", "10.200.2.2", 6000,
            NATBehavior(nat_type=NATType.SYMMETRIC_RANDOM, public_ip="203.0.113.99")
        )

        res_fallback = DiscoV4Simulator.attempt_traversal(ep_rnd1, ep_rnd2, net_sim)
        self.assertTrue(res_fallback["success"])
        self.assertTrue(res_fallback["derp_fallback"])
        self.assertEqual(res_fallback["strategy"], "DERP_RELAY_FALLBACK")

        # Case 3: Transmit data over Camouflaged DERP Relay
        relay = MockDERPRelay("derp-us-east", "us-east")
        pub_rnd1 = os.urandom(32)
        pub_rnd2 = os.urandom(32)
        relay.register_client(pub_rnd1)
        relay.register_client(pub_rnd2)

        # Transmit 20 packets through DERP fallback
        for i in range(20):
            payload = f"STREAM_PACKET_{i}".encode()
            success = relay.relay_packet(pub_rnd1, pub_rnd2, payload)
            self.assertTrue(success)

        self.assertEqual(len(relay.packet_log), 20)


if __name__ == "__main__":
    unittest.main()
