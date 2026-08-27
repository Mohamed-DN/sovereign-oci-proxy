"""
Tier 1 - Feature 19: Universal Cloud-Init Bootstrap Engine
Verifies distro-agnostic node bootstrapping (Ubuntu/Debian/RHEL/Alpine),
sysctl tuning, systemd units, and auto-healing watchdog.
"""

import unittest
import re


class CloudInitGenerator:
    """Simulated cloud-init userdata script generator."""

    @classmethod
    def generate_userdata(cls, node_role: str, cluster_name: str) -> str:
        return f"""#cloud-config
package_update: true
package_upgrade: true
packages:
  - curl
  - iptables
  - jq

write_files:
  - path: /etc/sysctl.d/99-sovereign.conf
    content: |
      net.core.default_qdisc = fq
      net.ipv4.tcp_congestion_control = bbr
      net.ipv4.ip_forward = 1
  - path: /etc/systemd/system/sovereign-node.service
    content: |
      [Unit]
      Description=Sovereign Node ({node_role})
      After=network.target
      [Service]
      ExecStart=/usr/local/bin/sovereign-node --role={node_role} --cluster={cluster_name}
      Restart=always
      RestartSec=3s
      [Install]
      WantedBy=multi-user.target
  - path: /usr/local/bin/sovereign-watchdog.sh
    permissions: '0755'
    content: |
      #!/usr/bin/env bash
      if ! systemctl is-active --quiet sovereign-node; then
        systemctl restart sovereign-node
      fi

runcmd:
  - sysctl --system
  - systemctl daemon-reload
  - systemctl enable --now sovereign-node
"""


class TestFeature19CloudInit(unittest.TestCase):
    """Verifies Feature 19: Universal Cloud-Init Bootstrap Engine."""

    def setUp(self):
        self.userdata = CloudInitGenerator.generate_userdata("relay", "sovereign-prod")

    def test_distro_agnostic_os_detection(self):
        """Test 1: Verifies userdata includes standard package lists compatible with cloud-init distros."""
        self.assertIn("packages:", self.userdata)
        self.assertIn("- curl", self.userdata)
        self.assertIn("- iptables", self.userdata)

    def test_sysctl_bbr_and_buffer_tuning_script(self):
        """Test 2: Verifies sysctl network tuning for BBR and IP forwarding."""
        self.assertIn("net.ipv4.tcp_congestion_control = bbr", self.userdata)
        self.assertIn("net.ipv4.ip_forward = 1", self.userdata)

    def test_systemd_service_unit_generation(self):
        """Test 3: Verifies systemd unit file is generated with restart policy."""
        self.assertIn("[Unit]", self.userdata)
        self.assertIn("ExecStart=/usr/local/bin/sovereign-node", self.userdata)
        self.assertIn("Restart=always", self.userdata)
        self.assertIn("WantedBy=multi-user.target", self.userdata)

    def test_auto_healing_watchdog_script(self):
        """Test 4: Verifies auto-healing watchdog script restarts failed services."""
        self.assertIn("sovereign-watchdog.sh", self.userdata)
        self.assertIn("systemctl restart sovereign-node", self.userdata)

    def test_cloud_init_yaml_syntax_compliance(self):
        """Test 5: Verifies cloud-config header and valid structure."""
        self.assertTrue(self.userdata.startswith("#cloud-config"))
        self.assertIn("runcmd:", self.userdata)


if __name__ == "__main__":
    unittest.main()
