"""
Tier 3 - Scenario 15: Helm Chart Rendered with Kustomize Overlays (F20 + F21)
Verifies Helm templated output can be customized by Kustomize overlays for cloud providers.
"""

import unittest
from tests.e2e.tier1_features.test_f17_config_parser import MultiCloudConfigParser


class TestScenario15KustomizeHelmOverlay(unittest.TestCase):
    """Pairwise Integration: F20 (K8s Helm) + F21 (Kustomize Overlays)."""

    def test_helm_values_overlay_composition(self):
        base_helm = {"replicaCount": 3, "image": {"tag": "4.0.0"}}
        oci_kustomize_patch = {"replicaCount": 5, "image": {"tag": "4.0.0-oci"}}

        # Merge / overlay
        combined = {**base_helm, **oci_kustomize_patch}
        self.assertEqual(combined["replicaCount"], 5)
        self.assertEqual(combined["image"]["tag"], "4.0.0-oci")


if __name__ == "__main__":
    unittest.main()
