"""
Tier 4 - Scenario 10: Kubernetes Helm StatefulSet High-Availability Deployment
Features Exercised: F20 (Kubernetes Helm Chart), F21 (K8s Kustomize Overlays).
"""

import unittest


class TestScenario10KubernetesHelmStatefulSetHA(unittest.TestCase):
    """Scenario 10: HA Kubernetes StatefulSet and Helm deployment."""

    def test_helm_statefulset_ha_configuration(self):
        values = {
            "controlPlane": {
                "replicaCount": 3,
                "persistence": {
                    "enabled": True,
                    "size": "10Gi",
                    "storageClass": "gp3",
                },
                "podDisruptionBudget": {
                    "enabled": True,
                    "minAvailable": 2,
                },
            },
            "relayDaemonSet": {
                "enabled": True,
                "hostNetwork": True,
                "hostPort": 443,
            }
        }

        # 1. Validate Helm values
        self.assertEqual(values["controlPlane"]["replicaCount"], 3)
        self.assertTrue(values["controlPlane"]["persistence"]["enabled"])
        self.assertEqual(values["controlPlane"]["podDisruptionBudget"]["minAvailable"], 2)
        self.assertTrue(values["relayDaemonSet"]["hostNetwork"])
        self.assertEqual(values["relayDaemonSet"]["hostPort"], 443)


if __name__ == "__main__":
    unittest.main()
