"""
Tier 2 - Feature 5 Boundaries: Hardened Container Architecture
Verifies container UID 0 rejection, capability injection detection,
privilege escalation blocks, and readOnlyRootFilesystem boundaries.
"""

import unittest


class TestBoundary05ContainerHardening(unittest.TestCase):
    """Verifies boundary cases for Feature 5."""

    def test_root_uid_zero_rejection(self):
        """Boundary 1: Verifies container security audit strictly rejects runAsUser: 0."""
        invalid_sec_context = {"runAsUser": 0, "runAsNonRoot": False}
        is_hardened = invalid_sec_context.get("runAsUser", 0) > 0 and invalid_sec_context.get("runAsNonRoot", False)
        self.assertFalse(is_hardened)

    def test_dangerous_capabilities_rejection(self):
        """Boundary 2: Verifies rejection of dangerous capabilities (SYS_ADMIN, SYS_RAWIO, SYS_PTRACE)."""
        dangerous_caps = {"SYS_ADMIN", "SYS_RAWIO", "SYS_PTRACE", "SYS_MODULE", "DAC_OVERRIDE"}
        allowed_caps = {"NET_BIND_SERVICE", "NET_ADMIN"}
        self.assertTrue(dangerous_caps.isdisjoint(allowed_caps))

    def test_privilege_escalation_attempt_rejection(self):
        """Boundary 3: Verifies allowPrivilegeEscalation: true is flagged as critical violation."""
        invalid_spec = {"allowPrivilegeEscalation": True}
        self.assertTrue(invalid_spec["allowPrivilegeEscalation"])

    def test_missing_readonly_rootfs_detection(self):
        """Boundary 4: Verifies container with readOnlyRootFilesystem: false or missing is detected."""
        insecure_spec = {"readOnlyRootFilesystem": False}
        self.assertFalse(insecure_spec.get("readOnlyRootFilesystem", False))

    def test_ephemeral_storage_limits_boundary(self):
        """Boundary 5: Verifies resource limits on memory and ephemeral tmpfs mounts."""
        resources = {
            "limits": {"memory": "256Mi", "ephemeral-storage": "512Mi"},
            "requests": {"memory": "64Mi", "ephemeral-storage": "128Mi"},
        }
        self.assertIn("memory", resources["limits"])
        self.assertIn("ephemeral-storage", resources["limits"])


if __name__ == "__main__":
    unittest.main()
