"""
Tier 2 - Feature 14 Boundaries: Exit Node Geolocation & Host Routing
Verifies case sensitivity normalization (us -> US), empty queries, 3-letter codes,
path traversal in Host IDs, and empty mesh pools.
"""

import unittest
from tests.harness import MockMeshNetwork


class TestBoundary14GeoRouting(unittest.TestCase):
    """Verifies boundary cases for Feature 14."""

    def setUp(self):
        self.mesh = MockMeshNetwork()

    def test_case_insensitive_country_code_normalization(self):
        """Boundary 1: Verifies lowercase 'us', 'de', 'jp' match correctly."""
        for code in ["us", "de", "jp"]:
            node = self.mesh.route_by_country(code)
            self.assertIsNotNone(node)
            self.assertEqual(node.geoip.country_code, code.upper())

    def test_empty_string_country_code(self):
        """Boundary 2: Verifies querying with empty string returns None."""
        node = self.mesh.route_by_country("")
        self.assertIsNone(node)

    def test_invalid_alpha3_and_numeric_codes(self):
        """Boundary 3: Verifies 3-letter (USA) or numeric (840) codes return None."""
        for code in ["USA", "DEU", "JPN", "840", "123"]:
            node = self.mesh.route_by_country(code)
            self.assertIsNone(node)

    def test_host_id_path_traversal_and_special_chars(self):
        """Boundary 4: Verifies malicious Host IDs ('../root', '<script>') return None."""
        malicious_ids = ["../exit-us-01", "exit-us-01/../../", "<script>alert(1)</script>", "exit-us-01\0"]
        for hid in malicious_ids:
            node = self.mesh.route_by_host_id(hid)
            self.assertIsNone(node)

    def test_all_nodes_offline_empty_mesh(self):
        """Boundary 5: Verifies system handles state when all exit nodes are deregistered."""
        self.mesh.exit_nodes.clear()
        node = self.mesh.route_by_country("US")
        self.assertIsNone(node)


if __name__ == "__main__":
    unittest.main()
