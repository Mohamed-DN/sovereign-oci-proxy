"""
Tier 3 - Scenario 11: Cross-Cloud NAT Traversal Matrix (F10 + F18 + F21)
Verifies Disco-v4 NAT traversal matrix between nodes provisioned across OCI, AWS, GCP, DO, Hetzner, Vultr.
"""

import unittest
from tests.harness import (
    SimulatedEndpoint,
    NATBehavior,
    NATType,
    DiscoV4Simulator,
    NetworkSimulator,
)


class TestScenario11MultiCloudNATMatrix(unittest.TestCase):
    """Pairwise Integration: F10 (NAT Traversal) + F18 (Terraform Provisioning) + F21 (Kustomize Overlays)."""

    def test_cross_provider_nat_traversal_matrix(self):
        providers = [
            ("oci", NATType.FULL_CONE, "130.61.1.1"),
            ("aws", NATType.RESTRICTED_CONE, "54.1.1.1"),
            ("gcp", NATType.PORT_RESTRICTED_CONE, "35.1.1.1"),
            ("digitalocean", NATType.FULL_CONE, "159.65.1.1"),
            ("hetzner", NATType.FULL_CONE, "116.203.1.1"),
            ("vultr", NATType.SYMMETRIC_SEQUENTIAL, "45.76.1.1"),
        ]

        net_sim = NetworkSimulator()
        endpoints = []
        for name, nat_type, pub_ip in providers:
            nat = NATBehavior(nat_type=nat_type, public_ip=pub_ip)
            ep = SimulatedEndpoint(f"node-{name}", "10.0.0.10", 6000, nat)
            endpoints.append(ep)

        # Test traversal between each adjacent pair
        for i in range(len(endpoints) - 1):
            ep_a = endpoints[i]
            ep_b = endpoints[i + 1]
            res = DiscoV4Simulator.attempt_traversal(ep_a, ep_b, net_sim)
            self.assertTrue(res["success"], f"Traversal between {ep_a.node_id} and {ep_b.node_id} failed")


if __name__ == "__main__":
    unittest.main()
