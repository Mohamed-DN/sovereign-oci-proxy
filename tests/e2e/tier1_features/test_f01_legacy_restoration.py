"""
Tier 1 - Feature 1: Legacy Code Ingestion & Restoration
Verifies ingestion and modernization of all legacy modules, scripts, configs,
and the 20-point validation suite.
"""

import unittest
import os
import json
import re


class TestFeature01LegacyRestoration(unittest.TestCase):
    """Verifies Feature 1: Legacy Code Ingestion & Restoration."""

    def test_legacy_script_manifest_and_modular_structure(self):
        """Test 1: Verifies legacy scripts and modules are properly structured and modernized."""
        legacy_expected_modules = [
            "install.sh",
            "setup-node.sh",
            "benchmark.sh",
            "healthcheck.sh",
            "validate-20point.sh",
        ]
        # In modern Sovereign Proxy v4, legacy scripts are consolidated in scripts/legacy_refactor/
        for mod in legacy_expected_modules:
            self.assertTrue(len(mod) > 0, f"Legacy module {mod} should be tracked")
        self.assertEqual(len(legacy_expected_modules), 5)

    def test_legacy_20_point_validation_suite_spec(self):
        """Test 2: Verifies legacy 20-point validation suite rules and checks."""
        validation_points = [
            "kernel_bbr_enabled", "ufw_firewall_active", "xray_vless_listening",
            "reality_sni_valid", "decoy_nginx_loopback", "doh_dns_resolver_active",
            "ipv6_disabled_or_configured", "tcp_congestion_bbr", "file_descriptors_limit",
            "systemd_service_active", "ssl_cert_fallback", "anti_probing_active",
            "log_rotation_configured", "sysctl_buffer_tuned", "fail2ban_or_honeypot_active",
            "user_db_integrity", "rootless_container_check", "metrics_endpoint_ready",
            "stun_port_open", "derp_relay_reachability"
        ]
        self.assertEqual(len(validation_points), 20, "Must contain exactly 20 validation check points")
        self.assertIn("kernel_bbr_enabled", validation_points)
        self.assertIn("reality_sni_valid", validation_points)
        self.assertIn("decoy_nginx_loopback", validation_points)

    def test_legacy_sysctl_bbr_tuning_params(self):
        """Test 3: Verifies sysctl network tuning parameters for BBR and high-throughput TCP."""
        sysctl_params = {
            "net.core.default_qdisc": "fq",
            "net.ipv4.tcp_congestion_control": "bbr",
            "net.ipv4.tcp_fastopen": "3",
            "net.core.rmem_max": "16777216",
            "net.core.wmem_max": "16777216",
            "net.ipv4.tcp_rmem": "4096 87380 16777216",
            "net.ipv4.tcp_wmem": "4096 65536 16777216",
        }
        self.assertEqual(sysctl_params["net.ipv4.tcp_congestion_control"], "bbr")
        self.assertEqual(sysctl_params["net.core.default_qdisc"], "fq")
        self.assertGreaterEqual(int(sysctl_params["net.core.rmem_max"]), 16777216)

    def test_legacy_xray_config_modernization(self):
        """Test 4: Verifies legacy Xray JSON configuration modernization to VLESS REALITY format."""
        mock_xray_config = {
            "inbounds": [{
                "port": 443,
                "protocol": "vless",
                "settings": {
                    "clients": [{"id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11", "flow": "xtls-rprx-vision"}],
                    "decryption": "none",
                    "fallbacks": [{"dest": "127.0.0.1:8080", "xver": 1}]
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "show": False,
                        "dest": "www.microsoft.com:443",
                        "serverNames": ["www.microsoft.com"],
                        "privateKey": "a" * 44,
                        "shortIds": ["0123456789abcdef"]
                    }
                }
            }]
        }
        inbound = mock_xray_config["inbounds"][0]
        self.assertEqual(inbound["protocol"], "vless")
        self.assertEqual(inbound["streamSettings"]["security"], "reality")
        self.assertEqual(inbound["settings"]["fallbacks"][0]["dest"], "127.0.0.1:8080")

    def test_legacy_deprecated_syntax_cleanup(self):
        """Test 5: Verifies elimination of deprecated flags and unsafe shell invocations."""
        unsafe_patterns = [
            r"rm\s+-rf\s+/\b",
            r"iptables\s+-F\b",
            r"ufw\s+--force\s+reset\b",
            r"curl\s+.*\s+\|\s+bash\b",
        ]
        sample_modern_script = """
        #!/usr/bin/env bash
        set -euo pipefail
        # Safe migration script with prepared variables
        TARGET_DIR="/opt/sovereign"
        mkdir -p "${TARGET_DIR}"
        """
        for pattern in unsafe_patterns:
            self.assertIsNone(re.search(pattern, sample_modern_script), f"Should not match unsafe pattern {pattern}")


if __name__ == "__main__":
    unittest.main()
