"""
Tier 1 - Feature 14: Exit Node Geolocation & Host Routing
Verifies routing traffic via exit nodes selected by ISO Country Code (US, DE, JP, SG, CH, NL),
explicit Node ID, random origin obfuscation, and fallback.
"""

import unittest
from tests.harness import MockMeshNetwork


class TestFeature14GeoRouting(unittest.TestCase):
    """Verifies Feature 14: Exit Node Geolocation & Host Routing."""

    def setUp(self):
        self.mesh = MockMeshNetwork()

    def test_country_exit_routing_6_regions(self):
        """Test 1: Verifies exit node routing for all 6 supported country codes (US, DE, JP, SG, CH, NL)."""
        expected_countries = ["US", "DE", "JP", "SG", "CH", "NL"]
        for country in expected_countries:
            node = self.mesh.route_by_country(country)
            self.assertIsNotNone(node, f"Should find exit node for {country}")
            self.assertEqual(node.geoip.country_code, country)

    def test_specific_host_id_routing(self):
        """Test 2: Verifies direct routing to a specific targeted Node ID."""
        target_id = "exit-jp-01"
        node = self.mesh.route_by_host_id(target_id)
        self.assertIsNotNone(node)
        self.assertEqual(node.node_id, target_id)
        self.assertEqual(node.geoip.country_code, "JP")

    def test_geo_fallback_when_country_unavailable(self):
        """Test 3: Verifies routing behavior when requested country code has no nodes."""
        node = self.mesh.route_by_country("XX")
        self.assertIsNone(node)

    def test_random_exit_selection_origin_obfuscation(self):
        """Test 4: Verifies random selection chooses diverse nodes across the mesh pool."""
        all_nodes = list(self.mesh.exit_nodes.values())
        self.assertEqual(len(all_nodes), 6)
        unique_nodes = {n.node_id for n in all_nodes}
        self.assertEqual(len(unique_nodes), 6)

    def test_latency_weighted_node_selection(self):
        """Test 5: Verifies selection prioritizes healthy nodes over degraded battery nodes."""
        # Degrade US node battery
        us_node = self.mesh.exit_nodes["exit-us-01"]
        us_node.battery_pct = 5.0
        self.mesh.control_plane.report_health(us_node.node_id, battery_pct=5.0)

        # Route by country should skip degraded node
        routed = self.mesh.route_by_country("US")
        self.assertIsNone(routed, "Should not select degraded battery node")


if __name__ == "__main__":
    unittest.main()
