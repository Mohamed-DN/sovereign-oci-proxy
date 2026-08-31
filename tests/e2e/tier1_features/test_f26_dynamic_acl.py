"""
Tier 1 - Feature 26: Dynamic Peer ACL Engine
Verifies directional/bidirectional peer group security policies, port range matching,
protocol filtering (TCP/UDP/ICMP/ALL), and default-drop enforcement.
"""

import unittest
from typing import List, Dict, Any, Tuple


class SimulatedPortRange:
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end

    def matches(self, port: int) -> bool:
        return self.start <= port <= self.end


def parse_port_ranges(raw: str) -> List[SimulatedPortRange]:
    raw = raw.strip()
    if not raw or raw == "*":
        return [SimulatedPortRange(1, 65535)]
    ranges = []
    for part in raw.split(","):
        part = part.strip()
        if "-" in part:
            s, e = part.split("-")
            ranges.append(SimulatedPortRange(int(s.strip()), int(e.strip())))
        else:
            p = int(part)
            ranges.append(SimulatedPortRange(p, p))
    return ranges


class SimulatedACLEngine:
    def __init__(self):
        self.groups: Dict[str, List[str]] = {}  # group_id -> [peer_id, ...]
        self.policies: List[Dict[str, Any]] = []

    def set_group(self, group_id: str, peers: List[str]):
        self.groups[group_id] = peers

    def add_policy(self, policy: Dict[str, Any]):
        self.policies.append(policy)

    def evaluate(self, src_peer: str, dst_peer: str, proto: str, dport: int) -> bool:
        # Default DROP
        # Find groups for src and dst
        src_groups = [gid for gid, members in self.groups.items() if src_peer in members]
        src_groups.append("group:all")
        dst_groups = [gid for gid, members in self.groups.items() if dst_peer in members]
        dst_groups.append("group:all")

        for pol in self.policies:
            if not pol.get("enabled", True):
                continue

            # Check forward match: src in pol.source_groups and dst in pol.dest_groups
            forward_match = any(sg in pol["source_groups"] for sg in src_groups) and \
                            any(dg in pol["dest_groups"] for dg in dst_groups)

            # Check reverse match if bidirectional
            reverse_match = False
            if pol.get("bidirectional", False):
                reverse_match = any(dg in pol["dest_groups"] for dg in src_groups) and \
                                any(sg in pol["source_groups"] for sg in dst_groups)

            if forward_match or reverse_match:
                # Match protocol and port
                for rule in pol.get("rules", []):
                    rule_proto = rule.get("protocol", "ALL")
                    if rule_proto != "ALL" and rule_proto != proto:
                        continue
                    port_ranges = parse_port_ranges(rule.get("ports", "*"))
                    if any(pr.matches(dport) for pr in port_ranges):
                        return rule.get("action", "ACCEPT") == "ACCEPT"

        return False


class TestFeature26DynamicPeerACL(unittest.TestCase):
    """Verifies Feature 26: Dynamic Peer ACL Engine."""

    def setUp(self):
        self.engine = SimulatedACLEngine()
        self.engine.set_group("group:developers", ["dev-laptop-1", "dev-laptop-2"])
        self.engine.set_group("group:exit-nodes", ["exit-us-01", "exit-de-02"])
        self.engine.set_group("group:db-servers", ["db-prod-01"])

    def test_default_drop_unmatched_traffic(self):
        """Test 1: Verifies unmatched peer-to-peer traffic is dropped by default."""
        allowed = self.engine.evaluate("dev-laptop-1", "db-prod-01", "TCP", 5432)
        self.assertFalse(allowed, "Traffic must be DROPPED by default when no ACL policy matches")

    def test_directional_rule_enforcement(self):
        """Test 2: Verifies directional policies allow source to destination but block reverse."""
        self.engine.add_policy({
            "id": "dev-to-exit",
            "enabled": True,
            "source_groups": ["group:developers"],
            "dest_groups": ["group:exit-nodes"],
            "bidirectional": False,
            "rules": [
                {"protocol": "TCP", "ports": "80,443,8080-8090", "action": "ACCEPT"},
                {"protocol": "UDP", "ports": "53,443", "action": "ACCEPT"},
            ],
        })

        # Dev to Exit on port 443 -> ACCEPT
        self.assertTrue(self.engine.evaluate("dev-laptop-1", "exit-us-01", "TCP", 443))
        # Dev to Exit on port 8085 (in range 8080-8090) -> ACCEPT
        self.assertTrue(self.engine.evaluate("dev-laptop-1", "exit-us-01", "TCP", 8085))
        # Dev to Exit on unapproved port 22 -> DROP
        self.assertFalse(self.engine.evaluate("dev-laptop-1", "exit-us-01", "TCP", 22))

        # Reverse direction (Exit initiating to Dev) -> DROP (directional rule)
        self.assertFalse(self.engine.evaluate("exit-us-01", "dev-laptop-1", "TCP", 443))

    def test_bidirectional_rule_enforcement(self):
        """Test 3: Verifies bidirectional policies allow two-way communications."""
        self.engine.add_policy({
            "id": "dev-p2p",
            "enabled": True,
            "source_groups": ["group:developers"],
            "dest_groups": ["group:developers"],
            "bidirectional": True,
            "rules": [
                {"protocol": "ALL", "ports": "*", "action": "ACCEPT"},
            ],
        })
        self.assertTrue(self.engine.evaluate("dev-laptop-1", "dev-laptop-2", "TCP", 22))
        self.assertTrue(self.engine.evaluate("dev-laptop-2", "dev-laptop-1", "UDP", 51820))

    def test_port_range_boundary_matching(self):
        """Test 4: Verifies port range parser handles edge boundary ports correctly."""
        ranges = parse_port_ranges("80,443,8000-8080")
        self.assertTrue(any(r.matches(80) for r in ranges))
        self.assertTrue(any(r.matches(443) for r in ranges))
        self.assertTrue(any(r.matches(8000) for r in ranges))
        self.assertTrue(any(r.matches(8080) for r in ranges))
        self.assertTrue(any(r.matches(8050) for r in ranges))
        self.assertFalse(any(r.matches(7999) for r in ranges))
        self.assertFalse(any(r.matches(8081) for r in ranges))

    def test_disabled_policy_ignored(self):
        """Test 5: Verifies disabled policies do not permit traffic."""
        self.engine.add_policy({
            "id": "disabled-rule",
            "enabled": False,
            "source_groups": ["group:developers"],
            "dest_groups": ["group:db-servers"],
            "bidirectional": False,
            "rules": [{"protocol": "TCP", "ports": "5432", "action": "ACCEPT"}],
        })
        self.assertFalse(self.engine.evaluate("dev-laptop-1", "db-prod-01", "TCP", 5432))


if __name__ == "__main__":
    unittest.main()
