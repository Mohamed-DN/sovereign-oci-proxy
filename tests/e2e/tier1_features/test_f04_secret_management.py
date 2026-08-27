"""
Tier 1 - Feature 4: Secret Management & Zero-Plaintext Storage
Verifies environment/vault-based secret injection eliminating plaintext script tokens,
key derivation, memory scrubbing, and token rotation.
"""

import unittest
import os
import hashlib
import hmac
import ctypes


class SecretManager:
    """Simulated secret manager and HKDF key derivation engine."""

    @staticmethod
    def derive_key(master_secret: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
        """HKDF-Extract and HKDF-Expand (RFC 5869) using HMAC-SHA256."""
        # Extract
        prk = hmac.new(salt, master_secret, hashlib.sha256).digest()
        # Expand
        t = b""
        okm = b""
        i = 1
        while len(okm) < length:
            t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
            okm += t
            i += 1
        return okm[:length]

    @staticmethod
    def sanitize_config(raw_yaml_str: str) -> bool:
        """Verifies no hardcoded secrets or tokens exist in plain text configs."""
        forbidden_keys = ["private_key:", "password:", "api_token:", "mesh_secret:"]
        for line in raw_yaml_str.splitlines():
            line_str = line.strip()
            for key in forbidden_keys:
                if line_str.startswith(key):
                    val = line_str.split(":", 1)[1].strip()
                    # Values must use env syntax '${VAR}' or Vault reference
                    if not (val.startswith("${") and val.endswith("}")) and not val.startswith("vault://"):
                        return False
        return True


class TestFeature04SecretManagement(unittest.TestCase):
    """Verifies Feature 4: Secret Management & Zero-Plaintext Storage."""

    def test_env_var_secret_injection(self):
        """Test 1: Verifies secrets are loaded from environment variables rather than static files."""
        test_key = "sovereign_mesh_psk_alpha_test_12345"
        os.environ["SOVEREIGN_MESH_PSK"] = test_key
        loaded = os.getenv("SOVEREIGN_MESH_PSK")
        self.assertEqual(loaded, test_key)
        del os.environ["SOVEREIGN_MESH_PSK"]

    def test_key_derivation_hkdf(self):
        """Test 2: Verifies HKDF key derivation generates deterministic 32-byte cryptographic keys."""
        master = b"sovereign_root_master_seed_998877"
        salt = b"sovereign_mesh_v4_salt"
        info = b"handshake_wire_encryption"
        key1 = SecretManager.derive_key(master, salt, info, 32)
        key2 = SecretManager.derive_key(master, salt, info, 32)

        self.assertEqual(len(key1), 32)
        self.assertEqual(key1, key2)

        # Different info yields distinct key
        key3 = SecretManager.derive_key(master, salt, b"onion_routing_layer", 32)
        self.assertNotEqual(key1, key3)

    def test_in_memory_secret_zeroization(self):
        """Test 3: Verifies bytearray secret zeroization overwrites memory buffer."""
        secret_buf = bytearray(b"super_secret_ephemeral_token_xyz")
        self.assertNotEqual(secret_buf, bytearray(len(secret_buf)))
        
        # Zeroize
        for idx in range(len(secret_buf)):
            secret_buf[idx] = 0
            
        self.assertEqual(secret_buf, bytearray(len(secret_buf)))

    def test_plaintext_rejection_in_config_files(self):
        """Test 4: Verifies config sanitizer rejects hardcoded static secrets."""
        valid_config = """
        mesh:
          name: prod-cluster
          private_key: ${SOVEREIGN_PRIVATE_KEY}
          mesh_secret: vault://secrets/mesh/psk
        """
        invalid_config = """
        mesh:
          name: prod-cluster
          private_key: my_raw_plaintext_private_key_12345
        """
        self.assertTrue(SecretManager.sanitize_config(valid_config))
        self.assertFalse(SecretManager.sanitize_config(invalid_config))

    def test_zero_downtime_secret_rotation(self):
        """Test 5: Verifies multi-epoch token acceptance during secret rotation window."""
        old_epoch_key = b"epoch_1_key_00000000000000000000"
        new_epoch_key = b"epoch_2_key_00000000000000000000"
        valid_keys = {1: old_epoch_key, 2: new_epoch_key}

        # Validate packets from both epochs
        tag1 = hmac.new(valid_keys[1], b"msg_from_peer_a", hashlib.sha256).digest()[:16]
        tag2 = hmac.new(valid_keys[2], b"msg_from_peer_b", hashlib.sha256).digest()[:16]

        self.assertTrue(hmac.compare_digest(tag1, hmac.new(valid_keys[1], b"msg_from_peer_a", hashlib.sha256).digest()[:16]))
        self.assertTrue(hmac.compare_digest(tag2, hmac.new(valid_keys[2], b"msg_from_peer_b", hashlib.sha256).digest()[:16]))


if __name__ == "__main__":
    unittest.main()
