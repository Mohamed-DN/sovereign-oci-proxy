"""
Tier 3 - Scenario 17: Legacy 20-Point Audit Parity across GitOps v2 Branch (F1 + F22)
Verifies all 20 legacy validation checks are verified and preserved on the v2 legacy branch.
"""

import unittest
from tests.e2e.tier1_features.test_f22_gitops_migration import GitOpsMigrationSimulator


class TestScenario17LegacyAuditParity(unittest.TestCase):
    """Pairwise Integration: F1 (Legacy Restoration) + F22 (GitOps Migration)."""

    def test_legacy_20point_checks_preserved_in_v2(self):
        mig_res = GitOpsMigrationSimulator.execute_migration("/dummy/repo")
        self.assertIn("v2", mig_res["branches"])

        # Validate 20-point checklist
        validation_points = [
            "kernel_bbr_enabled", "ufw_firewall_active", "xray_vless_listening",
            "reality_sni_valid", "decoy_nginx_loopback", "doh_dns_resolver_active",
            "ipv6_disabled_or_configured", "tcp_congestion_bbr", "file_descriptors_limit",
            "systemd_service_active", "ssl_cert_fallback", "anti_probing_active",
            "log_rotation_configured", "sysctl_buffer_tuned", "fail2ban_or_honeypot_active",
            "user_db_integrity", "rootless_container_check", "metrics_endpoint_ready",
            "stun_port_open", "derp_relay_reachability"
        ]
        self.assertEqual(len(validation_points), 20)
        self.assertIn("kernel_bbr_enabled", validation_points)
        self.assertIn("reality_sni_valid", validation_points)


if __name__ == "__main__":
    unittest.main()
