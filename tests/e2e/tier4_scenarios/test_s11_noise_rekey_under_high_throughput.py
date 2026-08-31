"""
Tier 4 - Scenario 11: Noise Session Re-Keying Under High-Throughput Stream
Features Exercised: F11 (Noise Cryptographic Plane), F12 (DirectFrame SVRN Framing).
"""

import unittest
import os
from tests.harness import DirectFrame


class TestScenario11NoiseRekeyUnderHighThroughput(unittest.TestCase):
    """Scenario 11: Noise session re-keying under sustained high packet throughput."""

    def test_noise_session_rekeying_flow(self):
        initial_key = os.urandom(32)
        rekeyed_key = os.urandom(32)
        sender_pub = os.urandom(32)

        # 1. Transmit frames under initial session key
        frames_session_1 = []
        for seq in range(1, 51):
            frame = DirectFrame(sender_pubkey=sender_pub, payload=f"DATA_PKT_{seq}".encode())
            raw = frame.serialize(key=initial_key)
            frames_session_1.append(raw)

        self.assertEqual(len(frames_session_1), 50)

        # Verify all parsed correctly with initial key
        for idx, raw in enumerate(frames_session_1, 1):
            parsed = DirectFrame.parse(raw, key=initial_key)
            self.assertEqual(parsed.payload, f"DATA_PKT_{idx}".encode())

        # 2. Trigger In-Flight Session Rekeying
        frames_session_2 = []
        for seq in range(1, 51):
            frame = DirectFrame(sender_pubkey=sender_pub, payload=f"REKEY_DATA_{seq}".encode())
            raw = frame.serialize(key=rekeyed_key)
            frames_session_2.append(raw)

        # Old key fails on new session frames (AEAD auth failure)
        with self.assertRaises(ValueError):
            DirectFrame.parse(frames_session_2[0], key=initial_key)

        # New key successfully decrypts new session frames
        for idx, raw in enumerate(frames_session_2, 1):
            parsed = DirectFrame.parse(raw, key=rekeyed_key)
            self.assertEqual(parsed.payload, f"REKEY_DATA_{idx}".encode())


if __name__ == "__main__":
    unittest.main()
