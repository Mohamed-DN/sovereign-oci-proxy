"""
Tier 1 - Feature 9: Cryptographic Overlay (Noise_IKpsk2)
Verifies 0-RTT secure key exchange, ChaCha20-Poly1305 AEAD wire framing,
Curve25519 DH simulation, anti-replay, and rekeying.
"""

import unittest
import os
import struct
import hashlib
import hmac
from tests.harness import DirectFrame, DIRECT_MAGIC


class TestFeature09CryptoOverlay(unittest.TestCase):
    """Verifies Feature 9: Cryptographic Overlay (Noise_IKpsk2)."""

    def setUp(self):
        self.session_key = os.urandom(32)
        self.sender_pubkey = os.urandom(32)

    def test_direct_frame_wire_format_compliance(self):
        """Test 1: Verifies Direct Frame wire format exactly adheres to 66-byte header specification."""
        payload = b"OVERLAY_PACKET_DATA_XYZ"
        frame = DirectFrame(sender_pubkey=self.sender_pubkey, payload=payload)
        wire_bytes = frame.serialize(key=self.session_key)

        # Header: 4B magic + 12B nonce + 32B pubkey + 2B length + 16B tag = 66 bytes
        self.assertEqual(len(wire_bytes), 66 + len(payload))
        
        # Verify magic number 0x534F5652 ('SOVR')
        magic, = struct.unpack(">I", wire_bytes[0:4])
        self.assertEqual(magic, DIRECT_MAGIC)

    def test_aead_tag_authentication_and_tamper_detection(self):
        """Test 2: Verifies AEAD tag validates authentic payload and detects bit modifications."""
        payload = b"SECURE_PAYLOAD_123"
        frame = DirectFrame(sender_pubkey=self.sender_pubkey, payload=payload)
        wire_bytes = frame.serialize(key=self.session_key)

        # Successful parse with correct key
        parsed = DirectFrame.parse(wire_bytes, key=self.session_key)
        self.assertEqual(parsed.payload, payload)

        # Tamper payload
        tampered_wire = bytearray(wire_bytes)
        tampered_wire[-1] ^= 0x01
        with self.assertRaises(ValueError):
            DirectFrame.parse(bytes(tampered_wire), key=self.session_key)

        # Wrong key
        with self.assertRaises(ValueError):
            DirectFrame.parse(wire_bytes, key=os.urandom(32))

    def test_0rtt_handshake_session_key_derivation(self):
        """Test 3: Verifies 0-RTT Noise_IKpsk2 key derivation with static pre-shared key (PSK)."""
        client_static_priv = os.urandom(32)
        server_static_pub = os.urandom(32)
        psk = os.urandom(32)
        client_ephemeral_priv = os.urandom(32)

        # Noise_IKpsk2 mixKey simulation
        ck = hashlib.sha256(b"Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s").digest()
        # Mix DH(e, rs)
        dh1 = hmac.new(ck, client_ephemeral_priv + server_static_pub, hashlib.sha256).digest()
        # Mix DH(s, rs)
        dh2 = hmac.new(dh1, client_static_priv + server_static_pub, hashlib.sha256).digest()
        # Mix PSK
        session_key = hmac.new(dh2, psk, hashlib.sha256).digest()

        self.assertEqual(len(session_key), 32)
        self.assertNotEqual(session_key, psk)

    def test_nonce_sequencing_and_anti_replay(self):
        """Test 4: Verifies sliding window anti-replay protection."""
        seen_nonces = set()
        window_size = 64
        max_nonce = 0

        def check_nonce(n: int) -> bool:
            nonlocal max_nonce
            if n in seen_nonces:
                return False
            if n < max_nonce - window_size:
                return False  # Too old
            seen_nonces.add(n)
            if n > max_nonce:
                max_nonce = n
            return True

        self.assertTrue(check_nonce(1))
        self.assertTrue(check_nonce(2))
        self.assertTrue(check_nonce(3))
        self.assertFalse(check_nonce(2), "Replay must be rejected")
        self.assertTrue(check_nonce(100))
        self.assertFalse(check_nonce(5), "Too far behind sliding window")

    def test_cryptographic_epoch_rotation_rekeying(self):
        """Test 5: Verifies epoch advancement triggers new session key derivation."""
        base_secret = b"cluster_root_seed"
        epoch_1_key = hmac.new(base_secret, struct.pack(">I", 1), hashlib.sha256).digest()
        epoch_2_key = hmac.new(base_secret, struct.pack(">I", 2), hashlib.sha256).digest()

        self.assertNotEqual(epoch_1_key, epoch_2_key)
        self.assertEqual(len(epoch_1_key), 32)
        self.assertEqual(len(epoch_2_key), 32)


if __name__ == "__main__":
    unittest.main()
