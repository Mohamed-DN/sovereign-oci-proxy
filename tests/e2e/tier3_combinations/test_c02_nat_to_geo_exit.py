"""
Tier 3 - Scenario 2: NAT Traversal to Country Geo Exit (F10 + F14 + F12)
Verifies client performing Disco-v4 NAT hole punching to connect directly to a
Country-selected (DE) client-bridge exit node.
"""

import unittest
from tests.harness import (
    MockMeshNetwork,
    SimulatedEndpoint,
    NATBehavior,
    NATType,
    DiscoV4Simulator,
)


class TestScenario02NATToGeoExit(unittest.TestCase):
    """Pairwise Integration: F10 (NAT Traversal) + F14 (Geo Routing) + F12 (Client Bridge)."""

    def test_nat_traversal_to_country_exit_egress(self):
        mesh = MockMeshNetwork()
        de_exit = mesh.route_by_country("DE")
        self.assertIsNotNone(de_exit)
        self.assertEqual(de_exit.geoip.country_code, "DE")

        # Client behind Restricted Cone NAT
        client_nat = NATBehavior(nat_type=NATType.RESTRICTED_CONE, public_ip="198.51.100.77")
        client_ep = SimulatedEndpoint("client-de-user", "192.168.1.50", 6100, client_nat)

        # Exit node behind Full Cone NAT
        exit_nat = NATBehavior(nat_type=NATType.FULL_CONE, public_ip="203.0.113.88")
        exit_ep = SimulatedEndpoint(de_exit.node_id, "10.0.0.88", 6100, exit_nat)

        # Traverse NAT
        res = DiscoV4Simulator.attempt_traversal(client_ep, exit_ep)
        self.assertTrue(res["success"])
        self.assertEqual(res["strategy"], "DIRECT_UDP_PUNCH")

        # Execute Egress through DE Exit Node
        ok, status, resp = de_exit.handle_egress_request(
            client_node_id="client-de-user",
            dest_ip="93.184.216.34",
            dest_port=443,
            payload=b"GET /de-content HTTP/1.1\r\n\r\n",
        )
        self.assertTrue(ok)
        self.assertIn(b"Hello from DE", resp)


if __name__ == "__main__":
    unittest.main()
