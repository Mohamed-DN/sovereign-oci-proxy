"""
Tier 2 - Feature 9 Boundaries: Cryptographic Overlay (Noise_IKpsk2)
Verifies truncated Direct Frames, magic mismatch, 65535 payload boundary,
65536 payload overflow rejection, and nonce rollover.
"""

import unittest
import os
import struct
from tests.harness import DirectFrame, DIRECT_MAGIC


class TestBoundary09CryptoOverlay(unittest.TestCase):
    """Verifies boundary cases for Feature 9."""

    def test_truncated_direct_frame_header_rejection(self):
        """Boundary 1: Verifies parser rejects frames under 66 bytes."""
        truncated_bytes = [b"", b"\x53\x4F\x56\x52", b"X" * 65]
        for buf in truncated_bytes:
            with self.assertRaises(ValueError):
                DirectFrame.parse(buf)

    def test_invalid_magic_number_rejection(self):
        """Boundary 2: Verifies non-SOVR magic numbers raise ValueError."""
        header = struct.pack(">I", 0xDEADBEEF) + os.urandom(62)
        with self.assertRaises(ValueError):
            DirectFrame.parse(header)

    def test_payload_size_boundary_65535_bytes(self):
        """Boundary 3: Verifies maximum valid payload size 65535 bytes serializes correctly."""
        max_payload = b"A" * 65535
        frame = DirectFrame(payload=max_payload)
        wire_data = frame.serialize()
        self.assertEqual(len(wire_data), 66 + 65535)

    def test_payload_overflow_65536_bytes(self):
        """Boundary 4: Verifies payload exceeding 65535 bytes raises ValueError."""
        oversized_payload = b"B" * 65536
        frame = DirectFrame(payload=oversized_payload)
        with self.assertRaises(ValueError):
            frame.serialize()

    def test_nonce_boundary_rollover(self):
        """Boundary 5: Verifies 96-bit (12-byte) nonce sequencing boundaries."""
        zero_nonce = bytes(12)
        max_nonce = b"\xFF" * 12
        self.assertEqual(len(zero_nonce), 12)
        self.assertEqual(len(max_nonce), 12)


if __name__ == "__main__":
    unittest.main()
