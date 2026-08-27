"""
Tier 1 - Feature 28: Real-time Peer Posture & Geo-Fencing Compliance
Verifies OS/client version validation, configurable Geo-Fencing with DEFAULT ALLOW
(ensuring RU, EG, CN, IN are not hardcoded blocked), security state checks, and quarantine handling.
"""

import unittest
from typing import Dict, List, Any, Optional, Tuple


def compare_semver(a: str, b: str) -> int:
    """Compares two semver strings (-1: a < b, 0: a == b, 1: a > b)."""
    a_clean = a.lstrip("v").split("-")[0].split("+")[0]
    b_clean = b.lstrip("v").split("-")[0].split("+")[0]
    a_parts = [int(p) for p in a_clean.split(".") if p.isdigit()]
    b_parts = [int(p) for p in b_clean.split(".") if p.isdigit()]

    max_len = max(len(a_parts), len(b_parts))
    a_parts.extend([0] * (max_len - len(a_parts)))
    b_parts.extend([0] * (max_len - len(b_parts)))

    for a_num, b_num in zip(a_parts, b_parts):
        if a_num < b_num:
            return -1
        if a_num > b_num:
            return 1
    return 0


class SimulatedPostureEngine:
    def __init__(self):
        self.policies: List[Dict[str, Any]] = []
        self.quarantined: Dict[str, str] = {}  # node_id -> reason

    def add_policy(self, policy: Dict[str, Any]):
        self.policies.append(policy)

    def evaluate(self, attestation: Dict[str, Any]) -> Tuple[bool, List[str]]:
        node_id = attestation.get("node_id", "unknown")
        failed = []

        for pol in self.policies:
            if not pol.get("enabled", True):
                continue

            # 1. Client Version
            min_client = pol.get("min_client_version")
            if min_client and attestation.get("client_version"):
                if compare_semver(attestation["client_version"], min_client) < 0:
                    failed.append(f"Client version {attestation['client_version']} < {min_client}")

            # 2. OS Version
            os_rules = pol.get("os_rules", [])
            for rule in os_rules:
                if rule["os_name"].lower() == attestation.get("os_name", "").lower():
                    if compare_semver(attestation.get("os_version", "0.0.0"), rule["min_version"]) < 0:
                        failed.append(f"OS version {attestation['os_version']} < {rule['min_version']}")

            # 3. Geo-Fencing: Configurable with DEFAULT ALLOW
            geo = pol.get("geo_rule", {})
            prohibited = geo.get("prohibited_countries", [])
            allowed = geo.get("allowed_countries", [])
            cc = attestation.get("country_code", "").upper().strip()

            if cc:
                # Blacklist check
                if prohibited and cc in [p.upper().strip() for p in prohibited]:
                    failed.append(f"Prohibited country {cc}")

                # Whitelist check
                if allowed and cc not in [a.upper().strip() for a in allowed]:
                    failed.append(f"Country {cc} not in allowed list")

            # 4. Security State Checks
            sec = pol.get("security_rule", {})
            if sec.get("require_disk_encryption") and not attestation.get("disk_encrypted", False):
                failed.append("Disk encryption required")
            if sec.get("require_firewall") and not attestation.get("firewall_active", False):
                failed.append("Firewall required")
            if sec.get("require_rootless") and not attestation.get("is_rootless", False):
                failed.append("Rootless execution required")

        if failed:
            self.quarantined[node_id] = "; ".join(failed)
            return False, failed
        else:
            self.quarantined.pop(node_id, None)
            return True, []


class TestFeature28PeerPosture(unittest.TestCase):
    """Verifies Feature 28: Real-time Peer Posture & Geo-Fencing."""

    def setUp(self):
        self.engine = SimulatedPostureEngine()

    def test_default_allow_for_censored_countries(self):
        """Test 1: Verifies Geo-Fencing is default ALLOW for all countries, including RU, EG, CN, IN."""
        # Default policy without geo restrictions
        self.engine.add_policy({
            "id": "default-policy",
            "enabled": True,
            "min_client_version": "4.0.0",
            "geo_rule": {
                "allowed_countries": [],    # Empty = allow all
                "prohibited_countries": [], # Empty = no blacklist
            },
        })

        censored_list = ["RU", "EG", "CN", "IN", "IR", "TR", "SA", "VN"]
        for cc in censored_list:
            att = {
                "node_id": f"node-{cc}",
                "os_name": "linux",
                "os_version": "6.1.0",
                "client_version": "4.0.0",
                "country_code": cc,
                "disk_encrypted": True,
                "firewall_active": True,
                "is_rootless": True,
            }
            compliant, failed = self.engine.evaluate(att)
            self.assertTrue(compliant, f"Country {cc} must be ALLOWED by default for censorship evasion, failed: {failed}")
            self.assertNotIn(f"node-{cc}", self.engine.quarantined)

    def test_explicit_blacklist_and_whitelist_enforcement(self):
        """Test 2: Verifies Geo-Fencing restrictions apply ONLY when explicitly configured."""
        self.engine.add_policy({
            "id": "restricted-geo",
            "enabled": True,
            "geo_rule": {
                "allowed_countries": ["US", "DE", "GB"],
                "prohibited_countries": ["KP"],
            },
        })

        # US is allowed
        att_us = {"node_id": "node-us", "country_code": "US", "client_version": "4.0.0"}
        comp_us, _ = self.engine.evaluate(att_us)
        self.assertTrue(comp_us)

        # FR is not in allowed list
        att_fr = {"node_id": "node-fr", "country_code": "FR", "client_version": "4.0.0"}
        comp_fr, _ = self.engine.evaluate(att_fr)
        self.assertFalse(comp_fr)
        self.assertIn("node-fr", self.engine.quarantined)

    def test_client_semver_posture_evaluation(self):
        """Test 3: Verifies outdated client versions are quarantined."""
        self.engine.add_policy({
            "id": "min-ver-policy",
            "enabled": True,
            "min_client_version": "4.0.0",
        })

        # Outdated client
        att_old = {"node_id": "node-old", "client_version": "v3.9.4"}
        comp, failed = self.engine.evaluate(att_old)
        self.assertFalse(comp)
        self.assertIn("node-old", self.engine.quarantined)

        # Upgraded client
        att_new = {"node_id": "node-old", "client_version": "v4.0.1"}
        comp_new, _ = self.engine.evaluate(att_new)
        self.assertTrue(comp_new)
        self.assertNotIn("node-old", self.engine.quarantined)

    def test_host_security_state_checks(self):
        """Test 4: Verifies disk encryption, firewall, and rootless requirements."""
        self.engine.add_policy({
            "id": "hardened-sec",
            "enabled": True,
            "security_rule": {
                "require_disk_encryption": True,
                "require_firewall": True,
                "require_rootless": True,
            },
        })

        att_insecure = {
            "node_id": "insecure-host",
            "disk_encrypted": False,
            "firewall_active": False,
            "is_rootless": False,
        }
        comp, failed = self.engine.evaluate(att_insecure)
        self.assertFalse(comp)
        self.assertEqual(len(failed), 3)

    def test_os_minimum_version_check(self):
        """Test 5: Verifies OS-specific minimum version enforcement."""
        self.engine.add_policy({
            "id": "os-policy",
            "enabled": True,
            "os_rules": [
                {"os_name": "darwin", "min_version": "14.0.0"},
                {"os_name": "linux", "min_version": "5.15.0"},
            ],
        })

        # macOS 13.5 < 14.0.0 -> Fail
        att_mac_old = {"node_id": "mac-old", "os_name": "darwin", "os_version": "13.5.0"}
        comp_mac, _ = self.engine.evaluate(att_mac_old)
        self.assertFalse(comp_mac)

        # macOS 14.5 >= 14.0.0 -> Pass
        att_mac_new = {"node_id": "mac-new", "os_name": "darwin", "os_version": "14.5.0"}
        comp_mac_new, _ = self.engine.evaluate(att_mac_new)
        self.assertTrue(comp_mac_new)


if __name__ == "__main__":
    unittest.main()
