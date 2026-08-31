"""
Tier 3 - Scenario 1: VLESS Ingress to Noise Overlay via DERP Relay (F6 + F9 + F11)
Verifies inbound VLESS REALITY connection encapsulated into a Noise_IKpsk2 Direct Frame
and relayed across a camouflaged DERP-v4 relay.
"""

import unittest
import uuid
import os
from tests.harness import (
    DirectFrame,
    DERPFrame,
    DERPPacketType,
    MockDERPRelay,
)
from tests.e2e.tier1_features.test_f06_vless_reality import VLESSRealityIngress


class TestScenario01VLESSToMeshRelay(unittest.TestCase):
    """Pairwise Integration: F6 (VLESS) + F9 (Crypto Overlay) + F11 (DERP Relay)."""

    def test_vless_connection_encapsulation_and_derp_relay(self):
        client_uuid = str(uuid.uuid4())
        ingress = VLESSRealityIngress(valid_uuids=[client_uuid], short_ids=["0123456789abcdef"])
        
        # Step 1: Ingress VLESS connection
        u_bytes = uuid.UUID(client_uuid).bytes
        vless_hdr = b"\x00" + u_bytes + b"\x00\x01\x01\xbb\x01\x08\x08\x08\x08"
        action, target = ingress.route_inbound_connection(vless_hdr, "www.microsoft.com")
        self.assertEqual(action, "PROXY_MESH")

        # Step 2: Encapsulate into Noise DirectFrame
        session_key = os.urandom(32)
        sender_pub = os.urandom(32)
        dest_pub = os.urandom(32)
        payload = b"HTTP_PROXY_PAYLOAD_VLESS_DATA"
        direct_frame = DirectFrame(sender_pubkey=sender_pub, payload=payload)
        direct_wire = direct_frame.serialize(key=session_key)

        # Step 3: Forward through DERP Relay
        relay = MockDERPRelay("derp-eu", "eu-central")
        relay.register_client(dest_pub)
        success = relay.relay_packet(sender_pub, dest_pub, direct_wire)
        self.assertTrue(success)

        # Step 4: Parse at receiver
        self.assertEqual(len(relay.packet_log), 1)
        relayed_record = relay.packet_log[0]
        self.assertEqual(relayed_record["dest"], dest_pub.hex())


if __name__ == "__main__":
    unittest.main()
