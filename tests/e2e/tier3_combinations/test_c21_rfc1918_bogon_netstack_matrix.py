"""
Tier 3 - Scenario 21: Exhaustive RFC 1918 Bogon Matrix on Client Bridge Egress (F13 + F12)
Verifies client bridge egress drops all RFC 1918, loopback, link-local, and multicast addresses.
"""

import unittest
from tests.harness import MockMeshNetwork, RFC1918LeakDetector


class TestScenario21RFC1918BogonNetstackMatrix(unittest.TestCase):
    """Pairwise Integration: F13 (RFC 1918 Isolation) + F12 (Client Bridge)."""

    def test_exhaustive_bogon_matrix_across_all_nodes(self):
        mesh = MockMeshNetwork()
        for node_id, exit_node in mesh.exit_nodes.items():
            result = RFC1918LeakDetector.audit_exit_node(exit_node)
            self.assertTrue(result.passed, f"Node {node_id} failed bogon isolation: {result.violations}")


if __name__ == "__main__":
    unittest.main()
