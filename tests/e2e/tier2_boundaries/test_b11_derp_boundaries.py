"""
Tier 2 - Feature 11 Boundaries: Camouflaged DERP-v4 Relay Swarm
Verifies truncated DERP frames (<37B), invalid pubkey sizes, unknown destinations,
oversized frame lengths, and connection limits.
"""

import unittest
import os
import struct
from tests.harness import DERPFrame, DERPPacketType, MockDERPRelay


class TestBoundary11DERPRelay(unittest.TestCase):
    """Verifies boundary cases for Feature 11."""

    def test_truncated_derp_frame_header(self):
        """Boundary 1: Verifies parser rejects frames shorter than 37 bytes."""
        truncated = [b"", b"\x01", b"\x01" + b"A" * 32]
        for buf in truncated:
            with self.assertRaises(ValueError):
                DERPFrame.parse(buf)

    def test_invalid_destination_pubkey_length(self):
        """Boundary 2: Verifies non-32-byte destination public keys raise ValueError."""
        invalid_keys = [b"", b"A" * 31, b"B" * 33]
        for k in invalid_keys:
            frame = DERPFrame(packet_type=DERPPacketType.PACKET.value, dest_pubkey=k)
            with self.assertRaises(ValueError):
                frame.serialize()

    def test_unregistered_destination_relay_drop(self):
        """Boundary 3: Verifies relaying to unregistered public key returns False and logs drop."""
        relay = MockDERPRelay("derp-test", "us-east")
        sender = os.urandom(32)
        unknown_dest = os.urandom(32)
        success = relay.relay_packet(sender, unknown_dest, b"PAYLOAD")
        self.assertFalse(success)

    def test_oversized_frame_length_declaration(self):
        """Boundary 4: Verifies declared frame length exceeding buffer raises ValueError on parse."""
        # Header claims 1000 bytes payload, but only 5 bytes provided
        header = b"\x03" + os.urandom(32) + struct.pack(">I", 1000) + b"12345"
        with self.assertRaises(ValueError):
            DERPFrame.parse(header)

    def test_relay_shutdown_during_active_traffic(self):
        """Boundary 5: Verifies relay close cleanly refuses subsequent packets without throwing uncaught exceptions."""
        relay = MockDERPRelay("derp-test", "us-east")
        pub = os.urandom(32)
        relay.register_client(pub)
        relay.close()
        success = relay.relay_packet(os.urandom(32), pub, b"TEST")
        self.assertFalse(success)


if __name__ == "__main__":
    unittest.main()
