"""
Tier 3 - Scenario 7: Unified Config to Terraform & Helm Values Pipeline (F17 + F18 + F20)
Verifies parsed YAML configs cleanly parameterize Terraform modules and Kubernetes Helm charts.
"""

import unittest
from tests.e2e.tier1_features.test_f17_config_parser import MultiCloudConfigParser


class TestScenario07ConfigToTerraformK8s(unittest.TestCase):
    """Pairwise Integration: F17 (Config Parser) + F18 (Terraform Provisioning) + F20 (K8s Helm)."""

    def test_pipeline_transforms_yaml_to_tf_and_helm(self):
        cluster_yaml = {
            "mesh": {
                "name": "sovereign-multi-prod",
                "overlay_cidr": "100.64.0.0/10",
            },
            "providers": [
                {"name": "aws", "region": "us-east-1", "nodes": [{"role": "control-plane", "shape": "t4g.small"}]},
                {"name": "gcp", "region": "europe-west3", "nodes": [{"role": "relay", "shape": "e2-small"}]},
            ]
        }
        parsed = MultiCloudConfigParser.validate_and_parse(cluster_yaml)

        # Generate Terraform inputs for AWS
        tfvars_aws = MultiCloudConfigParser.generate_tfvars(parsed, "aws")
        self.assertEqual(tfvars_aws["cluster_name"], "sovereign-multi-prod")
        self.assertEqual(tfvars_aws["region"], "us-east-1")

        # Generate Helm values
        helm_vals = MultiCloudConfigParser.generate_helm_values(parsed)
        self.assertEqual(helm_vals["global"]["clusterName"], "sovereign-multi-prod")
        self.assertEqual(helm_vals["global"]["overlayCidr"], "100.64.0.0/10")


if __name__ == "__main__":
    unittest.main()
