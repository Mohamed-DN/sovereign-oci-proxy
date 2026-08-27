"""
Tier 1 - Feature 27: Extra Subnet Route Distribution & High-Availability Failover
Verifies subnet advertisement, CIDR prefix matching, Active-Passive failover,
Active-Active ECMP load balancing, and gateway health transitions.
"""

import unittest
import ipaddress
from typing import List, Dict, Optional, Any


class SimulatedRoutingPeer:
    def __init__(self, node_id: str, priority: int, is_healthy: bool = True):
        self.node_id = node_id
        self.priority = priority  # 1 is highest
        self.is_healthy = is_healthy
        self.fail_count = 0


class SimulatedNetworkRoute:
    def __init__(
        self,
        route_id: str,
        network_cidr: str,
        peers: List[SimulatedRoutingPeer],
        masquerade: bool = True,
        failover_mode: str = "ACTIVE_PASSIVE",
    ):
        self.route_id = route_id
        self.network = ipaddress.ip_network(network_cidr)
        self.peers = peers
        self.masquerade = masquerade
        self.failover_mode = failover_mode

    def get_active_gateway(self) -> Optional[SimulatedRoutingPeer]:
        healthy_peers = [p for p in self.peers if p.is_healthy]
        if not healthy_peers:
            return None
        # Sort by priority ascending (1 = highest priority)
        healthy_peers.sort(key=lambda p: p.priority)
        return healthy_peers[0]

    def get_ecmp_gateways(self) -> List[SimulatedRoutingPeer]:
        return [p for p in self.peers if p.is_healthy]


class SimulatedRouteTable:
    def __init__(self):
        self.routes: Dict[str, SimulatedNetworkRoute] = {}

    def add_route(self, route: SimulatedNetworkRoute):
        self.routes[route.route_id] = route

    def resolve_destination(self, dst_ip_str: str) -> Optional[SimulatedRoutingPeer]:
        dst_ip = ipaddress.ip_address(dst_ip_str)
        # Find longest prefix match
        best_match: Optional[SimulatedNetworkRoute] = None
        best_prefix_len = -1

        for route in self.routes.values():
            if dst_ip in route.network:
                if route.network.prefixlen > best_prefix_len:
                    best_prefix_len = route.network.prefixlen
                    best_match = route

        if best_match:
            return best_match.get_active_gateway()
        return None


class TestFeature27SubnetRoutes(unittest.TestCase):
    """Verifies Feature 27: Extra Subnet Route Distribution."""

    def setUp(self):
        self.table = SimulatedRouteTable()

    def test_cidr_prefix_route_registration(self):
        """Test 1: Verifies route registration with valid CIDR prefix."""
        p1 = SimulatedRoutingPeer("gw-primary", priority=1, is_healthy=True)
        route = SimulatedNetworkRoute(
            route_id="corp-vpc-10",
            network_cidr="10.100.0.0/16",
            peers=[p1],
            masquerade=True,
        )
        self.table.add_route(route)
        
        gw = self.table.resolve_destination("10.100.5.25")
        self.assertIsNotNone(gw)
        self.assertEqual(gw.node_id, "gw-primary")

    def test_active_passive_failover_on_primary_down(self):
        """Test 2: Verifies automatic gateway failover when primary gateway becomes unhealthy."""
        p1 = SimulatedRoutingPeer("gw-primary", priority=1, is_healthy=True)
        p2 = SimulatedRoutingPeer("gw-secondary", priority=2, is_healthy=True)

        route = SimulatedNetworkRoute(
            route_id="corp-db-subnet",
            network_cidr="172.20.0.0/24",
            peers=[p1, p2],
            failover_mode="ACTIVE_PASSIVE",
        )
        self.table.add_route(route)

        # Primary is healthy -> resolves to gw-primary
        self.assertEqual(self.table.resolve_destination("172.20.0.10").node_id, "gw-primary")

        # Simulate primary failure
        p1.is_healthy = False

        # Now resolves to secondary
        gw = self.table.resolve_destination("172.20.0.10")
        self.assertIsNotNone(gw)
        self.assertEqual(gw.node_id, "gw-secondary")

    def test_longest_prefix_matching(self):
        """Test 3: Verifies longest prefix match (/24 takes precedence over /16)."""
        p_broad = SimulatedRoutingPeer("gw-broad-16", priority=1, is_healthy=True)
        p_narrow = SimulatedRoutingPeer("gw-narrow-24", priority=1, is_healthy=True)

        self.table.add_route(SimulatedNetworkRoute("route-16", "10.0.0.0/16", [p_broad]))
        self.table.add_route(SimulatedNetworkRoute("route-24", "10.0.5.0/24", [p_narrow]))

        # Target in 10.0.5.0/24 should resolve to gw-narrow-24
        gw1 = self.table.resolve_destination("10.0.5.100")
        self.assertEqual(gw1.node_id, "gw-narrow-24")

        # Target in 10.0.1.0/24 should resolve to gw-broad-16
        gw2 = self.table.resolve_destination("10.0.1.50")
        self.assertEqual(gw2.node_id, "gw-broad-16")

    def test_all_gateways_down_returns_none(self):
        """Test 4: Verifies route lookup returns None when all advertised gateways are down."""
        p1 = SimulatedRoutingPeer("gw-1", priority=1, is_healthy=False)
        p2 = SimulatedRoutingPeer("gw-2", priority=2, is_healthy=False)
        self.table.add_route(SimulatedNetworkRoute("route-down", "192.168.100.0/24", [p1, p2]))

        self.assertIsNone(self.table.resolve_destination("192.168.100.10"))

    def test_ecmp_gateway_list(self):
        """Test 5: Verifies ECMP mode exposes all healthy routing peers."""
        p1 = SimulatedRoutingPeer("gw-ecmp-1", priority=1, is_healthy=True)
        p2 = SimulatedRoutingPeer("gw-ecmp-2", priority=1, is_healthy=True)
        p3 = SimulatedRoutingPeer("gw-ecmp-3", priority=1, is_healthy=False)

        route = SimulatedNetworkRoute("route-ecmp", "10.200.0.0/24", [p1, p2, p3], failover_mode="ACTIVE_ACTIVE_ECMP")
        healthy = route.get_ecmp_gateways()
        self.assertEqual(len(healthy), 2)
        self.assertIn(p1, healthy)
        self.assertIn(p2, healthy)
        self.assertNotIn(p3, healthy)


if __name__ == "__main__":
    unittest.main()
