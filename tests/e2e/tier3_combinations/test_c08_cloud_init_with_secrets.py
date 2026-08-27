"""
Tier 3 - Scenario 8: Cloud-Init Bootstrap with Zero-Plaintext Secrets (F19 + F4)
Verifies cloud-init bootstrapping injecting environment-driven tokens and deriving node keys.
"""

import unittest
from tests.e2e.tier1_features.test_f19_cloud_init import CloudInitGenerator
from tests.e2e.tier1_features.test_f04_secret_management import SecretManager


class TestScenario08CloudInitWithSecrets(unittest.TestCase):
    """Pairwise Integration: F19 (Cloud-Init) + F4 (Secret Management)."""

    def test_cloud_init_with_zero_plaintext_token_derivation(self):
        userdata = CloudInitGenerator.generate_userdata("edge-gateway", "prod-cluster")
        
        # Verify no hardcoded secrets in cloud-init
        self.assertTrue(SecretManager.sanitize_config(userdata))

        # Simulate node bootstrapping deriving keys from injected master token
        master_secret = b"env_injected_master_token_123"
        node_privkey = SecretManager.derive_key(master_secret, b"node_salt", b"node_identity_privkey", 32)
        self.assertEqual(len(node_privkey), 32)


if __name__ == "__main__":
    unittest.main()
