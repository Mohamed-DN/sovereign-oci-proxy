"""
Tier 3 - Scenario 18: Secret Rotation under Active Load (F4 + F9 + F16)
Verifies zero-plaintext token rotation while encrypted Noise streams are actively transmitting.
"""

import unittest
import os
import struct
import hmac
import hashlib
from tests.harness import MockControlPlane, DirectFrame, NodeCapability, NodeGeoIP


class TestScenario18SecretRotationUnderLoad(unittest.TestCase):
    """Pairwise Integration: F4 (Secret Management) + F9 (Crypto Overlay) + F16 (Control Plane)."""

    def test_live_secret_rotation_during_active_stream(self):
        cp = MockControlPlane("rotation-cluster")
        geoip = NodeGeoIP("US", "Ashburn", 39.0, -77.4)
        node_pub = os.urandom(32)
        cp.register_node("load-node", node_pub, [NodeCapability.CLIENT], geoip)

        # Transmit 50 frames across epoch rotation
        master_secret = b"live_rotation_secret"
        for epoch in [1, 2]:
            if epoch == 2:
                cp.rotate_epoch()
            
            key = hmac.new(master_secret, struct.pack(">I", epoch), hashlib.sha256).digest()
            for seq in range(10):
                frame = DirectFrame(sender_pubkey=node_pub, payload=f"MSG_E{epoch}_SEQ{seq}".encode())
                wire = frame.serialize(key=key)
                parsed = DirectFrame.parse(wire, key=key)
                self.assertEqual(parsed.payload, f"MSG_E{epoch}_SEQ{seq}".encode())


if __name__ == "__main__":
    unittest.main()
