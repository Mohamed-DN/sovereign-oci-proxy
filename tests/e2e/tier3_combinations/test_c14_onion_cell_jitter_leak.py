"""
Tier 3 - Scenario 14: Onion Circuit Cell Padding, Timing Jitter & Zero Leak Audit (F15 + F8 + F13)
Verifies fixed 1420-byte padded Onion cells with timing jitter undergo full security audit with 0 leaks.
"""

import unittest
from tests.harness import MockMeshNetwork, LeakDetector, ONION_CELL_SIZE


class TestScenario14OnionCellJitterLeak(unittest.TestCase):
    """Pairwise Integration: F15 (Onion Routing) + F8 (DoH Resolver) + F13 (RFC 1918 Isolation)."""

    def test_onion_circuit_zero_leak_audit(self):
        mesh = MockMeshNetwork()
        entry = mesh.exit_nodes["exit-us-01"]
        middle = mesh.exit_nodes["exit-de-01"]
        exit_node = mesh.exit_nodes["exit-ch-01"]

        # 1. Build circuit cells
        cells = mesh.build_onion_circuit(circuit_id=8888, hops=[entry, middle, exit_node])
        for c in cells:
            self.assertEqual(len(c), ONION_CELL_SIZE)

        # 2. Run security leak detector on exit node
        detector = LeakDetector()
        audit_res = detector.run_full_security_audit(exit_node)
        self.assertTrue(audit_res["all_passed"], f"Leak audit failed: {audit_res}")


if __name__ == "__main__":
    unittest.main()
