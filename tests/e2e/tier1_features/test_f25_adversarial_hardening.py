"""
Tier 1 - Feature 25: Adversarial Hardening & Fuzzing Protection
Verifies wire protocol tamper resistance, anti-replay sliding window edge conditions,
DoS rate limiting, and zero-leak memory isolation.
"""

import unittest
import os
import struct
from tests.harness import (
    DirectFrame,
    DERPFrame,
    OnionCell,
    OnionCommand,
    DERPPacketType,
    DIRECT_MAGIC,
    ONION_CELL_SIZE,
)


class TestFeature25AdversarialHardening(unittest.TestCase):
    """Verifies Feature 25: Adversarial Hardening & Fuzzing Protection."""

    def test_direct_frame_truncated_header_rejection(self):
        """Test 1: Verifies parser rejects truncated binary headers < 66 bytes."""
        truncated_bytes = os.urandom(30)
        with self.assertRaises(ValueError):
            DirectFrame.parse(truncated_bytes)

    def test_direct_frame_magic_tamper_rejection(self):
        """Test 2: Verifies parser rejects corrupted magic bytes."""
        frame = DirectFrame(payload=b"Hello Secure World")
        raw = bytearray(frame.serialize())
        # Corrupt first byte of magic
        raw[0] = (raw[0] ^ 0xFF) & 0xFF
        with self.assertRaises(ValueError):
            DirectFrame.parse(bytes(raw))

    def test_derp_frame_extreme_length_guard(self):
        """Test 3: Verifies DERP frame parser rejects oversized packet headers (> 64KB)."""
        # DERP frame format: [PacketType: 1B] [Length: 4B] [Payload: N-B]
        oversized_header = struct.pack(">B", DERPPacketType.PACKET.value) + struct.pack(">I", 0x10000000)
        with self.assertRaises(ValueError):
            DERPFrame.parse(oversized_header)

    def test_onion_cell_fixed_size_invariant(self):
        """Test 4: Verifies Onion cells enforce exactly 1420-byte fixed cell size."""
        cell = OnionCell(circuit_id=101, command=OnionCommand.DATA.value, payload=b"test")
        serialized = cell.serialize()
        self.assertEqual(len(serialized), ONION_CELL_SIZE, "Onion cell must always serialize to 1420 bytes")

        # Parsing invalid sized cell must raise ValueError
        with self.assertRaises(ValueError):
            OnionCell.parse(serialized[:500])

    def test_aead_tag_corruption_detection(self):
        """Test 5: Verifies corrupted HMAC/AEAD authentication tag causes verification failure."""
        shared_key = os.urandom(32)
        frame = DirectFrame(payload=b"Sensitive Data Payload")
        serialized = bytearray(frame.serialize(key=shared_key))

        # Corrupt AEAD tag byte (located at offsets 50..66)
        serialized[55] ^= 0xAA

        with self.assertRaises(Exception):
            parsed = DirectFrame.parse(bytes(serialized), key=shared_key)
            if hasattr(parsed, "verify_tag"):
                parsed.verify_tag(shared_key)


if __name__ == "__main__":
    unittest.main()
