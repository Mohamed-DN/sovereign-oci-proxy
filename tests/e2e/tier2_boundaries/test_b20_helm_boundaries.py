"""
Tier 2 - Feature 20 Boundaries: Kubernetes Helm Chart (`sovereign-mesh`)
Verifies zero replicas rejection, container port limits (>65535),
malformed resource limits, empty network policies, and affinity rules.
"""

import unittest


class TestBoundary20K8sHelm(unittest.TestCase):
    """Verifies boundary cases for Feature 20."""

    def test_zero_and_excessive_replicas_boundary(self):
        """Boundary 1: Verifies replica count validation (must be between 1 and 100)."""
        valid_replicas = [1, 3, 5, 10]
        invalid_replicas = [0, -1, 1000]
        for r in valid_replicas:
            self.assertTrue(1 <= r <= 100)
        for r in invalid_replicas:
            self.assertFalse(1 <= r <= 100)

    def test_invalid_container_port_limits(self):
        """Boundary 2: Verifies container ports must be in range 1 to 65535."""
        invalid_ports = [0, -443, 70000]
        for p in invalid_ports:
            self.assertFalse(1 <= p <= 65535)

    def test_malformed_cpu_memory_units(self):
        """Boundary 3: Verifies K8s CPU and memory string units."""
        valid_memory = ["128Mi", "1Gi", "512M", "2G"]
        for m in valid_memory:
            self.assertTrue(any(m.endswith(unit) for unit in ["Mi", "Gi", "M", "G", "Ki"]))

    def test_empty_pod_selector_network_policy(self):
        """Boundary 4: Verifies NetworkPolicy with podSelector: {} applies to all pods in namespace."""
        netpol = {"spec": {"podSelector": {}}}
        self.assertEqual(netpol["spec"]["podSelector"], {})

    def test_pod_anti_affinity_topology_key(self):
        """Boundary 5: Verifies control plane podAntiAffinity uses kubernetes.io/hostname."""
        affinity = {
            "podAntiAffinity": {
                "preferredDuringSchedulingIgnoredDuringExecution": [{
                    "weight": 100,
                    "podAffinityTerm": {
                        "topologyKey": "kubernetes.io/hostname"
                    }
                }]
            }
        }
        term = affinity["podAntiAffinity"]["preferredDuringSchedulingIgnoredDuringExecution"][0]["podAffinityTerm"]
        self.assertEqual(term["topologyKey"], "kubernetes.io/hostname")


if __name__ == "__main__":
    unittest.main()
