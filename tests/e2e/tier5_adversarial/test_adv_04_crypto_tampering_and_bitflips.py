"""
Tier 5 - Adversarial Suite 4: Wire Protocol Tampering, Bit-Flipping & Truncation
Tests DirectFrame SVRN wire protocol and Onion cells against malicious payload modifications.
"""

import unittest
import os
from tests.harness import DirectFrame, OnionCell, MockMeshNetwork, ONION_CELL_SIZE


class TestAdversarial04CryptoTamperingAndBitflips(unittest.TestCase):
    """Adversarial crypto tampering and bit-flip tests."""

    def test_direct_frame_mac_authentication_tamper(self):
        key = os.urandom(32)
        frame = DirectFrame(payload=b"AUTHENTICATED_PLAINTEXT_PAYLOAD")
        wire_data = frame.serialize(key=key)

        # 1. Flip a single bit in the ciphertext / auth tag
        tampered_wire = bytearray(wire_data)
        tampered_wire[-5] ^= 0x01

        with self.assertRaises(Exception):
            DirectFrame.parse(bytes(tampered_wire), key=key)

    def test_direct_frame_magic_and_header_corruption(self):
        key = os.urandom(32)
        frame = DirectFrame(payload=b"TEST")
        wire_data = frame.serialize(key=key)

        # Corrupt magic bytes
        tampered_magic = b"XXXX" + wire_data[4:]
        with self.assertRaises(Exception):
            DirectFrame.parse(tampered_magic, key=key)

        # Truncate header
        truncated = wire_data[:10]
        with self.assertRaises(Exception):
            DirectFrame.parse(truncated, key=key)

    def test_onion_cell_tampering_all_hops(self):
        mesh = MockMeshNetwork()
        hops = [
            mesh.exit_nodes["exit-us-01"],
            mesh.exit_nodes["exit-de-01"],
            mesh.exit_nodes["exit-jp-01"],
        ]

        circuit_id = 0x55667788
        cells = mesh.build_onion_circuit(circuit_id, hops)
        self.assertEqual(len(cells), 3)

        # Tamper Layer 1
        tampered_l1 = bytearray(cells[0])
        tampered_l1[100] ^= 0xFF
        with self.assertRaises(ValueError):
            OnionCell.parse(bytes(tampered_l1), key=hops[0].privkey)

        # Tamper Layer 2
        tampered_l2 = bytearray(cells[1])
        tampered_l2[500] ^= 0xAA
        with self.assertRaises(ValueError):
            OnionCell.parse(bytes(tampered_l2), key=hops[1].privkey)

        # Tamper Layer 3
        tampered_l3 = bytearray(cells[2])
        tampered_l3[1400] ^= 0x55
        with self.assertRaises(ValueError):
            OnionCell.parse(bytes(tampered_l3), key=hops[2].privkey)


if __name__ == "__main__":
    unittest.main()
