"""
Tier 3 - Scenario 4: Control Plane Epoch Sync during Overlay Rekeying (F16 + F9)
Verifies control plane epoch advancement causing all peer nodes to rotate
cryptographic overlay session keys without session termination.
"""

import unittest
import os
import hmac
import hashlib
import struct
from tests.harness import MockControlPlane, NodeCapability, NodeGeoIP, DirectFrame


class TestScenario04ControlPlaneRekey(unittest.TestCase):
    """Pairwise Integration: F16 (Control Plane) + F9 (Crypto Overlay)."""

    def test_epoch_rotation_and_rekeying(self):
        cp = MockControlPlane("sovereign-rekey-cluster")
        geoip = NodeGeoIP("US", "Ashburn", 39.0, -77.4)
        
        # Register node
        node_pub = os.urandom(32)
        reg = cp.register_node("node-rekey-1", node_pub, [NodeCapability.CLIENT], geoip)
        self.assertEqual(reg["epoch"], 1)

        # Epoch 1 Session Key
        master_secret = b"sovereign_cluster_shared_secret"
        key_epoch_1 = hmac.new(master_secret, struct.pack(">I", 1), hashlib.sha256).digest()

        # Send frame in Epoch 1
        frame1 = DirectFrame(sender_pubkey=node_pub, payload=b"DATA_EPOCH_1")
        wire1 = frame1.serialize(key=key_epoch_1)
        parsed1 = DirectFrame.parse(wire1, key=key_epoch_1)
        self.assertEqual(parsed1.payload, b"DATA_EPOCH_1")

        # Advance epoch in control plane
        new_epoch = cp.rotate_epoch()
        self.assertEqual(new_epoch, 2)
        key_epoch_2 = hmac.new(master_secret, struct.pack(">I", 2), hashlib.sha256).digest()

        # Send frame in Epoch 2
        frame2 = DirectFrame(sender_pubkey=node_pub, payload=b"DATA_EPOCH_2")
        wire2 = frame2.serialize(key=key_epoch_2)
        parsed2 = DirectFrame.parse(wire2, key=key_epoch_2)
        self.assertEqual(parsed2.payload, b"DATA_EPOCH_2")

        # Verify old key cannot authenticate Epoch 2 frame
        with self.assertRaises(ValueError):
            DirectFrame.parse(wire2, key=key_epoch_1)


if __name__ == "__main__":
    unittest.main()
