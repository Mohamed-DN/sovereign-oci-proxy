"""
Tier 1 - Feature 10: Adaptive NAT Traversal (Disco-v4)
Verifies STUN classification, sequential port prediction, multi-port spraying for symmetric NATs,
and seamless DERP fallback.
"""

import unittest
from tests.harness import (
    NetworkSimulator,
    NATType,
    NATBehavior,
    SimulatedEndpoint,
    STUNSimulator,
    DiscoV4Simulator,
)


class TestFeature10NATTraversal(unittest.TestCase):
    """Verifies Feature 10: Adaptive NAT Traversal (Disco-v4)."""

    def setUp(self):
        self.net_sim = NetworkSimulator()
        self.stun_sim = STUNSimulator()

    def test_stun_nat_classification_matrix(self):
        """Test 1: Verifies STUN classification correctly identifies Cone and Symmetric NATs."""
        # Full Cone
        ep_full = SimulatedEndpoint("ep1", "192.168.1.10", 5000, NATBehavior(nat_type=NATType.FULL_CONE, public_ip="198.51.100.10"))
        self.assertEqual(self.stun_sim.classify_nat(ep_full), NATType.FULL_CONE)

        # Restricted Cone
        ep_restr = SimulatedEndpoint("ep2", "192.168.1.20", 5000, NATBehavior(nat_type=NATType.RESTRICTED_CONE, public_ip="198.51.100.20"))
        self.assertEqual(self.stun_sim.classify_nat(ep_restr), NATType.RESTRICTED_CONE)

        # Symmetric Sequential
        ep_sym_seq = SimulatedEndpoint("ep3", "192.168.1.30", 5000, NATBehavior(nat_type=NATType.SYMMETRIC_SEQUENTIAL, public_ip="198.51.100.30"))
        self.assertEqual(self.stun_sim.classify_nat(ep_sym_seq), NATType.SYMMETRIC_SEQUENTIAL)

    def test_cone_to_cone_direct_hole_punch(self):
        """Test 2: Verifies direct UDP hole punching succeeds between Cone NAT peers."""
        ep_a = SimulatedEndpoint("client-a", "192.168.1.10", 6000, NATBehavior(nat_type=NATType.FULL_CONE, public_ip="198.51.100.11"))
        ep_b = SimulatedEndpoint("client-b", "192.168.2.20", 6000, NATBehavior(nat_type=NATType.RESTRICTED_CONE, public_ip="203.0.113.22"))

        result = DiscoV4Simulator.attempt_traversal(ep_a, ep_b, self.net_sim)
        self.assertTrue(result["success"])
        self.assertEqual(result["strategy"], "DIRECT_UDP_PUNCH")
        self.assertFalse(result["derp_fallback"])

    def test_sequential_symmetric_port_prediction(self):
        """Test 3: Verifies port prediction accurately predicts mapped port for sequential symmetric NAT."""
        nat = NATBehavior(nat_type=NATType.SYMMETRIC_SEQUENTIAL, public_ip="198.51.100.50", base_port=45000, port_step=2)
        _, p1 = nat.get_mapped_endpoint("10.0.0.5", 5000, "1.1.1.1", 80)
        _, p2 = nat.get_mapped_endpoint("10.0.0.5", 5000, "2.2.2.2", 80)
        self.assertEqual(p2 - p1, 2, "Port delta must match step 2")

    def test_symmetric_multi_port_spraying(self):
        """Test 4: Verifies multi-port spraying establishes connectivity with symmetric NAT endpoint."""
        ep_cone = SimulatedEndpoint("cone-peer", "192.168.1.15", 7000, NATBehavior(nat_type=NATType.PORT_RESTRICTED_CONE, public_ip="198.51.100.99"))
        ep_sym = SimulatedEndpoint("sym-peer", "10.0.0.15", 7000, NATBehavior(nat_type=NATType.SYMMETRIC_SEQUENTIAL, public_ip="203.0.113.99", port_step=1))

        result = DiscoV4Simulator.attempt_traversal(ep_cone, ep_sym, self.net_sim, spray_count=16)
        self.assertTrue(result["success"])
        self.assertIn(result["strategy"], ("DIRECT_UDP_PUNCH", "SYMMETRIC_PORT_SPRAY"))

    def test_hostile_symmetric_derp_fallback(self):
        """Test 5: Verifies hostile Symmetric-Random to Symmetric-Random falls back smoothly to DERP."""
        ep_sym_rnd1 = SimulatedEndpoint("rnd1", "10.1.1.1", 8000, NATBehavior(nat_type=NATType.SYMMETRIC_RANDOM, public_ip="198.51.100.1"))
        ep_sym_rnd2 = SimulatedEndpoint("rnd2", "10.2.2.2", 8000, NATBehavior(nat_type=NATType.SYMMETRIC_RANDOM, public_ip="203.0.113.2"))

        result = DiscoV4Simulator.attempt_traversal(ep_sym_rnd1, ep_sym_rnd2, self.net_sim)
        self.assertTrue(result["success"])
        self.assertTrue(result["derp_fallback"])
        self.assertEqual(result["strategy"], "DERP_RELAY_FALLBACK")


if __name__ == "__main__":
    unittest.main()
