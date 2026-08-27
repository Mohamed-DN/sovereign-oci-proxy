"""
Tier 3 - Scenario 3: 3-Hop Onion via DERP Relays with Netstack Isolation (F15 + F11 + F13)
Verifies fixed 1420-byte Onion cells forwarded through DERP relays to exit node,
where netstack drops RFC 1918 private requests.
"""

import unittest
from tests.harness import MockMeshNetwork, OnionCell, ONION_CELL_SIZE


class TestScenario03OnionViaRelays(unittest.TestCase):
    """Pairwise Integration: F15 (Onion Routing) + F11 (DERP Relay) + F13 (RFC 1918 Isolation)."""

    def test_onion_cell_forwarding_and_exit_isolation(self):
        mesh = MockMeshNetwork()
        entry = mesh.exit_nodes["exit-us-01"]
        middle = mesh.exit_nodes["exit-de-01"]
        exit_node = mesh.exit_nodes["exit-jp-01"]

        # Build 3-hop circuit
        cells = mesh.build_onion_circuit(circuit_id=777, hops=[entry, middle, exit_node])
        self.assertEqual(len(cells), 3)
        for c in cells:
            self.assertEqual(len(c), ONION_CELL_SIZE)

        # Relay cell from client to entry through DERP relay
        relay = mesh.relays["us-east"]
        relayed = relay.relay_packet(entry.pubkey, middle.pubkey, cells[0])
        self.assertTrue(relayed)

        # Exit node receives malicious RFC 1918 probe
        ok_priv, status_priv, _ = exit_node.handle_egress_request("c1", "192.168.1.1", 80)
        self.assertFalse(ok_priv)
        self.assertIn("DROP_RFC1918_BOGON", status_priv)

        # Exit node receives legitimate public destination
        ok_pub, status_pub, resp = exit_node.handle_egress_request("c1", "93.184.216.34", 443)
        self.assertTrue(ok_pub)
        self.assertIn(b"Hello from JP", resp)


if __name__ == "__main__":
    unittest.main()
