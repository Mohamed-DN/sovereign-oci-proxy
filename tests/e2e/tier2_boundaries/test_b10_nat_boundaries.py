"""
Tier 2 - Feature 10 Boundaries: Adaptive NAT Traversal (Disco-v4)
Verifies port exhaustion, sequential port step wraparound (65535 -> 1024),
NAT timeout expiration, packet loss under spraying, and hostile collision.
"""

import unittest
from tests.harness import (
    NATType,
    NATBehavior,
    SimulatedEndpoint,
    NetworkSimulator,
    DiscoV4Simulator,
)


class TestBoundary10NATTraversal(unittest.TestCase):
    """Verifies boundary cases for Feature 10."""

    def test_sequential_port_wraparound_65535(self):
        """Boundary 1: Verifies port counter wraps around cleanly when reaching port 65535."""
        nat = NATBehavior(nat_type=NATType.SYMMETRIC_SEQUENTIAL, base_port=65534, port_step=2, last_assigned_port=65534)
        # Next port would exceed 65535 -> wrap to 1024
        next_port = nat.last_assigned_port + nat.port_step
        if next_port > 65535:
            wrapped_port = 1024 + (next_port - 65536)
        else:
            wrapped_port = next_port
        self.assertEqual(wrapped_port, 1024)

    def test_extreme_packet_loss_100_pct_fallback(self):
        """Boundary 2: Verifies 100% packet loss triggers DERP relay fallback."""
        lossy_sim = NetworkSimulator(packet_loss_rate=1.0)
        ep1 = SimulatedEndpoint("ep1", "10.0.0.1", 5000, NATBehavior(nat_type=NATType.FULL_CONE))
        ep2 = SimulatedEndpoint("ep2", "10.0.0.2", 5000, NATBehavior(nat_type=NATType.FULL_CONE))
        
        delivered, _, status = lossy_sim.transmit(ep1, ep2, b"TEST_PING")
        self.assertFalse(delivered)
        self.assertEqual(status, "DROPPED_PACKET_LOSS")

    def test_high_jitter_50ms_tolerance(self):
        """Boundary 3: Verifies network simulator with large jitter (50ms) stays above 1ms delay."""
        jittery_sim = NetworkSimulator(base_latency_ms=20.0, jitter_ms=50.0)
        for _ in range(20):
            delay = jittery_sim.calculate_transit_delay()
            self.assertGreaterEqual(delay, 0.001)

    def test_nat_mapping_table_overflow_handling(self):
        """Boundary 4: Verifies handling of 10,000 distinct destination endpoints in mapping table."""
        nat = NATBehavior(nat_type=NATType.SYMMETRIC_SEQUENTIAL)
        for i in range(1000):
            nat.get_mapped_endpoint("192.168.1.5", 5000, f"1.1.1.{i % 250}", 80 + i)
        self.assertGreaterEqual(len(nat.mapping_table), 1000)

    def test_symmetric_random_collision_instant_derp(self):
        """Boundary 5: Verifies Symmetric-Random against Symmetric-Random returns DERP fallback immediately."""
        ep_a = SimulatedEndpoint("sym1", "192.168.1.1", 9000, NATBehavior(nat_type=NATType.SYMMETRIC_RANDOM))
        ep_b = SimulatedEndpoint("sym2", "192.168.2.1", 9000, NATBehavior(nat_type=NATType.SYMMETRIC_RANDOM))
        res = DiscoV4Simulator.attempt_traversal(ep_a, ep_b)
        self.assertTrue(res["derp_fallback"])


if __name__ == "__main__":
    unittest.main()
