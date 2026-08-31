"""
Tier 2 - Feature 17 Boundaries: Unified Multi-Cloud Schema Parser
Verifies empty YAML documents, missing mesh blocks, unsupported providers,
invalid CIDR formats, and empty node lists.
"""

import unittest
from tests.e2e.tier1_features.test_f17_config_parser import MultiCloudConfigParser


class TestBoundary17ConfigParser(unittest.TestCase):
    """Verifies boundary cases for Feature 17."""

    def test_empty_config_dictionary(self):
        """Boundary 1: Verifies parser rejects completely empty config dictionary."""
        with self.assertRaises(ValueError):
            MultiCloudConfigParser.validate_and_parse({})

    def test_unsupported_cloud_provider_rejection(self):
        """Boundary 2: Verifies unsupported cloud provider (e.g. 'alicloud') raises ValueError."""
        config = {
            "mesh": {"name": "test", "overlay_cidr": "100.64.0.0/10"},
            "providers": [{"name": "alicloud", "region": "cn-hangzhou", "nodes": []}],
        }
        with self.assertRaises(ValueError):
            MultiCloudConfigParser.validate_and_parse(config)

    def test_missing_provider_region_or_nodes(self):
        """Boundary 3: Verifies provider block missing 'region' or 'nodes' is rejected."""
        config = {
            "mesh": {"name": "test", "overlay_cidr": "100.64.0.0/10"},
            "providers": [{"name": "aws"}],
        }
        with self.assertRaises(ValueError):
            MultiCloudConfigParser.validate_and_parse(config)

    def test_invalid_overlay_cidr_notation(self):
        """Boundary 4: Verifies malformed overlay CIDR notation raises ValueError."""
        config = {
            "mesh": {"name": "test", "overlay_cidr": "100.64.0.0.1/35"},
            "providers": [],
        }
        with self.assertRaises(ValueError):
            MultiCloudConfigParser.validate_and_parse(config)

    def test_tfvars_query_nonexistent_provider(self):
        """Boundary 5: Verifies generating tfvars for undeclared provider raises KeyError."""
        config = {
            "mesh": {"name": "test", "overlay_cidr": "100.64.0.0/10"},
            "providers": [{"name": "oci", "region": "us-ashburn-1", "nodes": []}],
        }
        parsed = MultiCloudConfigParser.validate_and_parse(config)
        with self.assertRaises(KeyError):
            MultiCloudConfigParser.generate_tfvars(parsed, "aws")


if __name__ == "__main__":
    unittest.main()
