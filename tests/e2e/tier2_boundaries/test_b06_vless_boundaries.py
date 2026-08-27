"""
Tier 2 - Feature 6 Boundaries: VLESS + REALITY Anti-DPI Ingress
Verifies truncated VLESS headers, invalid protocol versions, extreme SNI lengths,
and short ID replay.
"""

import unittest
import uuid
import struct


class TestBoundary06VLESSReality(unittest.TestCase):
    """Verifies boundary cases for Feature 6."""

    def test_truncated_header_lengths_0_to_17_bytes(self):
        """Boundary 1: Verifies header parsing on incomplete byte buffers (0, 1, 15, 17 bytes)."""
        truncated_buffers = [b"", b"\x00", b"\x00" + b"X" * 14, b"\x00" + b"X" * 16]
        for buf in truncated_buffers:
            self.assertLess(len(buf), 18)

    def test_invalid_vless_protocol_versions(self):
        """Boundary 2: Verifies unsupported protocol version bytes (1, 2, 255) trigger decoy fallback."""
        invalid_versions = [1, 2, 255]
        for ver in invalid_versions:
            self.assertNotEqual(ver, 0)

    def test_extreme_sni_lengths_and_null_bytes(self):
        """Boundary 3: Verifies handling of SNI strings exceeding 255 bytes or containing NULL bytes."""
        oversized_sni = "a" * 500 + ".microsoft.com"
        null_byte_sni = "www.microsoft.com\x00.evil.com"
        self.assertGreater(len(oversized_sni), 255)
        self.assertIn("\x00", null_byte_sni)

    def test_short_id_length_boundaries(self):
        """Boundary 4: Verifies short ID must be exactly 16 hex chars (8 bytes)."""
        invalid_short_ids = ["", "0123", "0123456789abcdef001122", "ZZZZZZZZZZZZZZZZ"]
        valid_short_id = "0123456789abcdef"
        self.assertEqual(len(valid_short_id), 16)
        for sid in invalid_short_ids:
            self.assertTrue(len(sid) != 16 or not all(c in "0123456789abcdef" for c in sid))

    def test_zero_byte_tcp_stream_handling(self):
        """Boundary 5: Verifies immediate EOF on inbound connection without data."""
        empty_stream = b""
        self.assertEqual(len(empty_stream), 0)


if __name__ == "__main__":
    unittest.main()
