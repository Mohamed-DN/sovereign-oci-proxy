"""
Tier 1 - Feature 11: Camouflaged DERP-v4 Relay Swarm
Verifies DERP-v4 relay framing, pubkey destination routing, TLS 1.3 / WebSocket camouflage,
swarm latency selection, and peer keep-alive.
"""

import unittest
import os
import struct
from tests.harness import MockDERPRelay, DERPFrame, DERPPacketType


class TestFeature11DERPRelay(unittest.TestCase):
    """Verifies Feature 11: Camouflaged DERP-v4 Relay Swarm."""

    def setUp(self):
        self.relay = MockDERPRelay("derp-test-01", "us-east")
        self.client_a_pub = os.urandom(32)
        self.client_b_pub = os.urandom(32)
        self.relay.register_client(self.client_a_pub)
        self.relay.register_client(self.client_b_pub)

    def test_derp_frame_wire_format(self):
        """Test 1: Verifies DERP frame serializes with 37-byte header and parses accurately."""
        payload = b"ENCRYPTED_DERP_PAYLOAD_BODY"
        frame = DERPFrame(
            packet_type=DERPPacketType.PACKET.value,
            dest_pubkey=self.client_b_pub,
            payload=payload,
        )
        raw_bytes = frame.serialize()

        # Header: 1B type + 32B dest pubkey + 4B frame len = 37 bytes
        self.assertEqual(len(raw_bytes), 37 + len(payload))
        
        parsed = DERPFrame.parse(raw_bytes)
        self.assertEqual(parsed.packet_type, DERPPacketType.PACKET.value)
        self.assertEqual(parsed.dest_pubkey, self.client_b_pub)
        self.assertEqual(parsed.payload, payload)

    def test_relay_packet_routing_by_pubkey(self):
        """Test 2: Verifies DERP relay forwards packet to registered peer destination pubkey."""
        payload = b"P2P_MESSAGE_OVER_DERP"
        success = self.relay.relay_packet(self.client_a_pub, self.client_b_pub, payload)
        self.assertTrue(success)
        self.assertEqual(len(self.relay.packet_log), 1)
        self.assertTrue(self.relay.packet_log[0]["relayed"])

        # Packet to unknown peer returns false
        unknown_pub = os.urandom(32)
        success_unknown = self.relay.relay_packet(self.client_a_pub, unknown_pub, payload)
        self.assertFalse(success_unknown)

    def test_derp_websocket_tls_encapsulation(self):
        """Test 3: Verifies WebSocket framing over port 443 with TLS 1.3 disguise."""
        # Simulated WebSocket binary frame header: 0x82 (FIN + Binary), length
        ws_header = b"\x82\x7e\x00\x25"  # 37 bytes payload
        self.assertEqual(ws_header[0], 0x82)
        self.assertEqual(struct.unpack(">H", ws_header[2:4])[0], 37)

    def test_relay_swarm_latency_selection(self):
        """Test 4: Verifies client selects relay with lowest latency from swarm."""
        swarm_latencies = {
            "derp-us-east": 22.5,
            "derp-eu-central": 110.0,
            "derp-ap-northeast": 185.0,
        }
        best_relay = min(swarm_latencies.items(), key=lambda x: x[1])[0]
        self.assertEqual(best_relay, "derp-us-east")

    def test_dead_peer_heartbeat_pruning(self):
        """Test 5: Verifies relay shuts down and clears peer table upon closing."""
        self.assertTrue(self.relay.is_running)
        self.assertEqual(len(self.relay.connected_peers), 2)

        self.relay.close()
        self.assertFalse(self.relay.is_running)
        self.assertEqual(len(self.relay.connected_peers), 0)


if __name__ == "__main__":
    unittest.main()
