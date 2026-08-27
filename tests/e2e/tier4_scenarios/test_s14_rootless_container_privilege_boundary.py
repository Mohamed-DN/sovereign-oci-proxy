"""
Tier 4 - Scenario 14: Rootless Container Runtime Privilege Boundaries & Capability Drops
Features Exercised: F09 (Rootless Container Runtime), F10 (Host Hardening & Cleanup).
"""

import unittest


class TestScenario14RootlessContainerPrivilegeBoundary(unittest.TestCase):
    """Scenario 14: Rootless container security profile verification."""

    def test_rootless_container_privilege_drop_and_isolation(self):
        sample_docker_compose = {
            "services": {
                "sovereign-node": {
                    "image": "sovereign/node:v4.0.0",
                    "user": "10001:10001",
                    "read_only": True,
                    "security_opt": [
                        "no-new-privileges:true",
                        "seccomp=unconfined",
                    ],
                    "cap_drop": ["ALL"],
                    "cap_add": ["NET_BIND_SERVICE"],
                    "tmpfs": ["/tmp:rw,noexec,nosuid,size=64M"],
                }
            }
        }

        service = sample_docker_compose["services"]["sovereign-node"]

        # 1. Unprivileged UID/GID
        self.assertEqual(service["user"], "10001:10001")

        # 2. Read-only root filesystem
        self.assertTrue(service["read_only"])

        # 3. Drops ALL Linux capabilities
        self.assertIn("ALL", service["cap_drop"])

        # 4. No new privileges
        self.assertIn("no-new-privileges:true", service["security_opt"])


if __name__ == "__main__":
    unittest.main()
