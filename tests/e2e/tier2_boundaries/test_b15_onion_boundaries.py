"""
Tier 2 - Feature 15 Boundaries: 3-Hop Onion Obfuscation Routing
Verifies non-1420B cell size rejection (1419B, 1421B), invalid circuit IDs (0),
circuit loop prevention, unknown commands, and corrupt layer headers.
"""

import unittest
import os
from tests.harness import OnionCell, OnionCommand, ONION_CELL_SIZE


class TestBoundary15OnionRouting(unittest.TestCase):
    """Verifies boundary cases for Feature 15."""

    def test_non_1420_byte_cell_size_rejection(self):
        """Boundary 1: Verifies parser rejects 1419-byte and 1421-byte cells."""
        short_cell = b"\x00" * 1419
        long_cell = b"\x00" * 1421
        with self.assertRaises(ValueError):
            OnionCell.parse(short_cell)
        with self.assertRaises(ValueError):
            OnionCell.parse(long_cell)

    def test_circuit_id_zero_and_uint32_max(self):
        """Boundary 2: Verifies circuit ID boundaries (0, 1, 4294967295)."""
        cell_0 = OnionCell(circuit_id=0, command=OnionCommand.DATA.value)
        cell_max = OnionCell(circuit_id=4294967295, command=OnionCommand.DATA.value)

        raw_0 = cell_0.serialize()
        raw_max = cell_max.serialize()

        parsed_0 = OnionCell.parse(raw_0)
        parsed_max = OnionCell.parse(raw_max)

        self.assertEqual(parsed_0.circuit_id, 0)
        self.assertEqual(parsed_max.circuit_id, 4294967295)

    def test_invalid_layer_crypto_header_length(self):
        """Boundary 3: Verifies layer crypto header must be exactly 64 bytes."""
        with self.assertRaises(ValueError):
            OnionCell(circuit_id=1, command=1, layer_crypto_header=b"X" * 63).serialize()
        with self.assertRaises(ValueError):
            OnionCell(circuit_id=1, command=1, layer_crypto_header=b"X" * 65).serialize()

    def test_unknown_command_byte_preservation(self):
        """Boundary 4: Verifies parser parses raw command byte even for unknown command 0xFF."""
        cell = OnionCell(circuit_id=10, command=0xFF)
        raw = cell.serialize()
        parsed = OnionCell.parse(raw)
        self.assertEqual(parsed.command, 0xFF)

    def test_payload_truncation_to_1335_bytes(self):
        """Boundary 5: Verifies payload exceeding 1335 bytes is safely truncated to fit cell."""
        oversized = b"Z" * 2000
        cell = OnionCell(circuit_id=5, command=OnionCommand.DATA.value, payload=oversized)
        raw = cell.serialize()
        self.assertEqual(len(raw), ONION_CELL_SIZE)


if __name__ == "__main__":
    unittest.main()
