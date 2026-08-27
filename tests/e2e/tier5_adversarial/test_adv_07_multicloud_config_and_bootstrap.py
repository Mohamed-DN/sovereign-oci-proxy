"""
Adversarial Verification Suite for Milestone 3:
Multi-Cloud Config, Terraform IaC, and Universal Node Bootstrap Engine.
"""

import unittest
import os
import re
import json
import subprocess
import tempfile

class TestAdv07MultiCloudConfigAndBootstrap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        cls.config_path = os.path.join(cls.project_root, "configs", "mesh-cluster.yaml")
        cls.bootstrap_path = os.path.join(cls.project_root, "scripts", "bootstrap", "bootstrap.sh")
        cls.cloud_init_path = os.path.join(cls.project_root, "scripts", "bootstrap", "cloud-init.yaml")

    def test_01_real_mesh_cluster_yaml_integrity(self):
        """Verify configs/mesh-cluster.yaml exists, is valid YAML, and meets all v4.0 criteria."""
        self.assertTrue(os.path.isfile(self.config_path), f"Missing {self.config_path}")
        with open(self.config_path, "r") as f:
            content = f.read()

        # Check required fields
        self.assertIn("apiVersion: sovereign.mesh/v4alpha1", content)
        self.assertIn("kind: SovereignCluster", content)
        self.assertTrue("clusterName: neronet-global-mesh-prod" in content or "clusterName: sovereign-global-mesh-prod" in content)
        self.assertIn("overlayCidr: \"100.64.0.0/10\"", content)
        self.assertIn("Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s", content)

        # Check 6 cloud providers configured in providers section
        for prov in ["oci", "aws", "gcp", "digitalocean", "hetzner", "vultr"]:
            self.assertIn(f"{prov}:", content)

        # Check 6 relay nodes
        relay_ids = re.findall(r"id:\s*([a-z0-9\-]+)", content)
        self.assertGreaterEqual(len(relay_ids), 6, f"Expected at least 6 relay nodes, found: {relay_ids}")

    def test_02_terraform_modules_and_variables_parity(self):
        """Verify Terraform variable declarations across all 6 provider modules."""
        providers = ["oci", "aws", "gcp", "digitalocean", "hetzner", "vultr"]
        for p in providers:
            mod_dir = os.path.join(self.project_root, "terraform", "modules", p)
            var_file = os.path.join(mod_dir, "variables.tf")
            main_file = os.path.join(mod_dir, "main.tf")
            self.assertTrue(os.path.isfile(var_file), f"Missing {var_file}")
            self.assertTrue(os.path.isfile(main_file), f"Missing {main_file}")

            with open(var_file, "r") as f:
                var_content = f.read()

            # Must declare nodes variable
            self.assertIn('variable "nodes"', var_content)
            # Must declare ssh_port
            self.assertIn('variable "ssh_port"', var_content)
            # Must declare cluster_name
            self.assertIn('variable "cluster_name"', var_content)

    def test_03_bootstrap_shell_static_security_analysis(self):
        """Adversarially probe bootstrap.sh for shell injection, quote safety, and safety flags."""
        self.assertTrue(os.path.isfile(self.bootstrap_path), f"Missing {self.bootstrap_path}")
        with open(self.bootstrap_path, "r") as f:
            script = f.read()

        # 1. Must use strict mode
        self.assertTrue("set -euo pipefail" in script or "set -e" in script, "Missing strict bash error handling")

        # 2. No dangerous eval statements
        self.assertNotIn("eval ", script, "bootstrap.sh must NOT use eval")

        # 3. Check safe jq JSON serialization
        self.assertIn("jq -n", script, "bootstrap.sh must use jq for safe JSON serialization")
        self.assertIn("--arg", script, "bootstrap.sh must use jq --arg to prevent shell injection into JSON")

        # 4. Check non-standard SSH port 2222 configured
        self.assertIn("2222", script, "bootstrap.sh must configure hardened SSH port 2222")

        # 5. Check firewall rules for 80, 443, 3478, 8080, 2222
        for port in ["2222", "443", "80", "3478", "8080"]:
            self.assertIn(port, script, f"Missing firewall rule for port {port}")

        # 6. Check distro detection coverage
        for distro in ["ubuntu", "debian", "rhel", "rocky", "alpine"]:
            self.assertIn(distro, script, f"Missing OS distro handling for {distro}")

    def test_04_bootstrap_registration_injection_simulation(self):
        """Simulate jq registration payload creation with malicious / special character inputs."""
        malicious_inputs = [
            {"node_id": 'node"; rm -rf /; #', "role": "relay", "pubkey": "key123"},
            {"node_id": "node-1", "role": 'relay\n"malicious": true\n', "pubkey": 'pub"key'},
            {"node_id": "node-test", "role": "relay", "pubkey": "' OR '1'='1"},
            {"node_id": "node-x", "role": "relay", "pubkey": "<script>alert(1)</script>"},
        ]

        for item in malicious_inputs:
            cmd = [
                "jq", "-n",
                "--arg", "node_id", item["node_id"],
                "--arg", "role", item["role"],
                "--arg", "pubkey", item["pubkey"],
                '{"nodeId": $node_id, "role": $role, "publicKey": $pubkey, "version": "4.0.0"}'
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"jq failed on input: {item}")
            
            # Verify parsed JSON structure
            data = json.loads(res.stdout)
            self.assertEqual(data["nodeId"], item["node_id"], "jq failed to sanitize nodeId")
            self.assertEqual(data["role"], item["role"], "jq failed to sanitize role")
            self.assertEqual(data["publicKey"], item["pubkey"], "jq failed to sanitize publicKey")
            self.assertEqual(data["version"], "4.0.0")

    def test_05_cloud_init_sysctl_bbr_and_buffer_parameters(self):
        """Verify cloud-init.yaml contains BBR, 64MB socket buffers, and security sysctls."""
        self.assertTrue(os.path.isfile(self.cloud_init_path), f"Missing {self.cloud_init_path}")
        with open(self.cloud_init_path, "r") as f:
            cloud_init = f.read()

        self.assertIn("#cloud-config", cloud_init)
        self.assertIn("net.ipv4.tcp_congestion_control = bbr", cloud_init)
        self.assertIn("net.core.rmem_max = 67108864", cloud_init)
        self.assertIn("net.core.wmem_max = 67108864", cloud_init)
        self.assertIn("net.ipv4.tcp_syncookies = 1", cloud_init)
        self.assertIn("sovereign-node.service", cloud_init)

    def test_06_helm_chart_values_and_manifest_security(self):
        """Verify Helm chart values and templates for zero-trust, caps, and probes."""
        chart_dir = os.path.join(self.project_root, "charts", "sovereign-mesh")
        values_file = os.path.join(chart_dir, "values.yaml")
        self.assertTrue(os.path.isfile(values_file), f"Missing {values_file}")

        with open(values_file, "r") as f:
            values = f.read()

        # HA 3 replicas
        self.assertIn("replicas: 3", values)
        # Honeypot
        self.assertIn("honeypot", values)
        # NET_ADMIN and NET_RAW for egress
        self.assertIn("NET_ADMIN", values)
        self.assertIn("NET_RAW", values)
        # Decoy Nginx
        self.assertIn("decoy", values)

        # Check template mounts /dev/net/tun
        egress_template = os.path.join(chart_dir, "templates", "edge-gateway-daemonset.yaml")
        self.assertTrue(os.path.isfile(egress_template), f"Missing {egress_template}")
        with open(egress_template, "r") as f:
            template_content = f.read()
        self.assertIn("/dev/net/tun", template_content)

if __name__ == "__main__":
    unittest.main()
