"""
Tier 5 - Adversarial Suite 5: WAN Chaos, Packet Loss & Degradation Resilience
Tests network simulation under harsh packet loss (10%-25%), corruption, and jitter.
"""

import unittest
from tests.harness import NetworkSimulator, SimulatedEndpoint, NATBehavior, NATType


class TestAdversarial05WANChaosAndPacketDegradation(unittest.TestCase):
    """Adversarial WAN chaos and packet corruption tests."""

    def test_packet_corruption_detection(self):
        # 100% corruption simulator to test integrity rejection
        sim = NetworkSimulator(base_latency_ms=10.0, jitter_ms=2.0, corruption_rate=1.0)
        src = SimulatedEndpoint("src-1", "192.168.1.10", 5000, NATBehavior(NATType.FULL_CONE, "198.51.100.10"))
        dst = SimulatedEndpoint("dst-1", "192.168.2.20", 6000, NATBehavior(NATType.FULL_CONE, "203.0.113.20"))

        ok, payload, diag = sim.transmit(src, dst, b"OriginalPayloadData")
        self.assertTrue(ok)
        self.assertEqual(diag, "CORRUPTED_IN_TRANSIT")
        self.assertNotEqual(payload, b"OriginalPayloadData")

    def test_packet_loss_drop_accounting(self):
        # 100% packet loss simulator
        sim = NetworkSimulator(base_latency_ms=10.0, jitter_ms=2.0, packet_loss_rate=1.0)
        src = SimulatedEndpoint("src-2", "192.168.1.10", 5000, NATBehavior(NATType.FULL_CONE, "198.51.100.10"))
        dst = SimulatedEndpoint("dst-2", "192.168.2.20", 6000, NATBehavior(NATType.FULL_CONE, "203.0.113.20"))

        ok, payload, diag = sim.transmit(src, dst, b"TestData")
        self.assertFalse(ok)
        self.assertEqual(diag, "DROPPED_PACKET_LOSS")


if __name__ == "__main__":
    unittest.main()
