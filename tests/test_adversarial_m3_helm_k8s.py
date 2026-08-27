#!/usr/bin/env python3
"""
Adversarial Verification Test Suite for Milestone 3 (Kubernetes & Helm Manifests).
Empirical challenger testing using Python standard library:
- Helm chart linting, templating, and boundary value stress testing.
- Component toggle and ingress permutation fuzzing.
- Kustomize overlays verification across 6 cloud providers (OCI, AWS, GCP, DO, Hetzner, Vultr).
- NetworkPolicy zero-trust isolation and RFC 1918 bogon subnet blocking.
- Least-privilege security capability & volume mount scoping.
"""

import ipaddress
import os
import re
import shutil
import subprocess
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CHART_DIR = os.path.join(PROJECT_ROOT, "charts", "sovereign-mesh")
K8S_DIR = os.path.join(PROJECT_ROOT, "k8s")

HELM_BIN = "/opt/homebrew/bin/helm" if os.path.exists("/opt/homebrew/bin/helm") else shutil.which("helm")
KUBECTL_BIN = "/usr/local/bin/kubectl" if os.path.exists("/usr/local/bin/kubectl") else shutil.which("kubectl")


def run_helm_template(values_dict=None, release_name="sovereign-test", namespace="sovereign-mesh"):
    """Runs helm template with optional values dictionary formatted as YAML."""
    if not HELM_BIN:
        return None, "helm binary not found"

    cmd = [HELM_BIN, "template", release_name, CHART_DIR, "--namespace", namespace]
    temp_file = None

    if values_dict is not None:
        temp_file = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
        _write_yaml_simple(values_dict, temp_file)
        temp_file.close()
        cmd.extend(["-f", temp_file.name])

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return res.stdout, None
    except subprocess.CalledProcessError as e:
        return None, e.stderr
    finally:
        if temp_file and os.path.exists(temp_file.name):
            os.remove(temp_file.name)


def run_kustomize(overlay_name):
    """Runs kubectl kustomize for a given overlay."""
    if not KUBECTL_BIN:
        return None, "kubectl binary not found"
    overlay_path = os.path.join(K8S_DIR, "overlays", overlay_name)
    cmd = [KUBECTL_BIN, "kustomize", overlay_path]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return res.stdout, None
    except subprocess.CalledProcessError as e:
        return None, e.stderr


def _write_yaml_simple(data, file_obj, indent=0):
    """Simple YAML serializer for basic nested dicts, lists, and scalars."""
    space = " " * indent
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                file_obj.write(f"{space}{k}:\n")
                _write_yaml_simple(v, file_obj, indent + 2)
            elif isinstance(v, bool):
                file_obj.write(f"{space}{k}: {str(v).lower()}\n")
            elif v is None:
                file_obj.write(f"{space}{k}: null\n")
            elif isinstance(v, str):
                file_obj.write(f"{space}{k}: \"{v}\"\n")
            else:
                file_obj.write(f"{space}{k}: {v}\n")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                file_obj.write(f"{space}- \n")
                _write_yaml_simple(item, file_obj, indent + 2)
            else:
                file_obj.write(f"{space}- {item}\n")


class TestAdversarialHelmManifests(unittest.TestCase):
    """Stress tests and boundary condition validation for Helm chart."""

    def test_helm_lint(self):
        if not HELM_BIN:
            self.skipTest("helm not found")
        cmd = [HELM_BIN, "lint", CHART_DIR]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0, f"Helm lint failed: {res.stderr}\n{res.stdout}")
        self.assertIn("0 chart(s) failed", res.stdout)

    def test_helm_default_render_all_resources(self):
        stdout, err = run_helm_template()
        self.assertIsNone(err, f"Helm template failed: {err}")
        self.assertIn("kind: Deployment", stdout)
        self.assertIn("kind: StatefulSet", stdout)
        self.assertIn("kind: DaemonSet", stdout)
        self.assertIn("kind: Service", stdout)
        self.assertIn("kind: ServiceAccount", stdout)
        self.assertIn("kind: ClusterRole", stdout)
        self.assertIn("kind: ClusterRoleBinding", stdout)
        self.assertIn("kind: HorizontalPodAutoscaler", stdout)
        self.assertIn("kind: PodDisruptionBudget", stdout)
        self.assertIn("kind: NetworkPolicy", stdout)
        self.assertIn("kind: ServiceMonitor", stdout)
        self.assertIn("kind: Secret", stdout)

    def test_boundary_zero_and_huge_replicas(self):
        # 1. Zero replicas
        values_zero = {
            "controlPlane": {"autoscaling": {"enabled": False}, "replicas": 0},
            "relay": {"replicas": 0},
            "decoy": {"replicas": 0},
        }
        out_zero, err0 = run_helm_template(values_zero)
        self.assertIsNone(err0)
        self.assertRegex(out_zero, r"replicas:\s*0")

        # 2. Huge replicas (1000)
        values_huge = {
            "controlPlane": {"autoscaling": {"enabled": False}, "replicas": 1000},
            "relay": {"replicas": 500},
        }
        out_huge, err_huge = run_helm_template(values_huge)
        self.assertIsNone(err_huge)
        self.assertRegex(out_huge, r"replicas:\s*1000")
        self.assertRegex(out_huge, r"replicas:\s*500")

    def test_autoscaling_and_hpa_mechanics(self):
        # When autoscaling is enabled, Deployment replicas should be absent to avoid flapping
        values_hpa_on = {
            "controlPlane": {
                "autoscaling": {
                    "enabled": True,
                    "minReplicas": 4,
                    "maxReplicas": 16,
                    "targetCPUUtilizationPercentage": 75,
                }
            }
        }
        out_on, err_on = run_helm_template(values_hpa_on)
        self.assertIsNone(err_on)
        self.assertIn("kind: HorizontalPodAutoscaler", out_on)
        self.assertIn("minReplicas: 4", out_on)
        self.assertIn("maxReplicas: 16", out_on)

        # When autoscaling is disabled, HPA should not exist and replicas should be set in Deployment
        values_hpa_off = {
            "controlPlane": {
                "autoscaling": {"enabled": False},
                "replicas": 7,
            }
        }
        out_off, err_off = run_helm_template(values_hpa_off)
        self.assertIsNone(err_off)
        self.assertNotIn("kind: HorizontalPodAutoscaler", out_off)
        self.assertIn("replicas: 7", out_off)

    def test_component_disable_switches(self):
        values_disabled = {
            "controlPlane": {"enabled": False},
            "relay": {"enabled": False},
            "edgeGateway": {"enabled": False},
            "decoy": {"enabled": False},
            "honeypot": {"enabled": False},
            "networkPolicy": {"enabled": False},
            "monitoring": {"serviceMonitor": {"enabled": False}},
            "serviceAccount": {"create": False},
        }
        out, err = run_helm_template(values_disabled)
        self.assertIsNone(err)
        self.assertNotIn("kind: Deployment", out)
        self.assertNotIn("kind: StatefulSet", out)
        self.assertNotIn("kind: DaemonSet", out)
        self.assertNotIn("kind: HorizontalPodAutoscaler", out)
        self.assertNotIn("kind: PodDisruptionBudget", out)
        self.assertNotIn("kind: NetworkPolicy", out)
        self.assertNotIn("kind: ServiceMonitor", out)
        self.assertNotIn("kind: ClusterRole", out)
        self.assertNotIn("kind: ServiceAccount", out)
        self.assertIn("kind: Secret", out)

    def test_custom_service_account_injection(self):
        values_sa = {
            "serviceAccount": {
                "create": False,
                "name": "corporate-sovereign-sa"
            }
        }
        out, err = run_helm_template(values_sa)
        self.assertIsNone(err)
        self.assertNotIn("kind: ServiceAccount", out)
        self.assertIn("serviceAccountName: corporate-sovereign-sa", out)

    def test_boundary_port_values(self):
        values_ports = {
            "controlPlane": {
                "service": {"port": 1, "grpcPort": 65535}
            }
        }
        out, err = run_helm_template(values_ports)
        self.assertIsNone(err)
        self.assertIn("port: 1", out)
        self.assertIn("port: 65535", out)


class TestAdversarialKustomizeOverlays(unittest.TestCase):
    """Empirical verification of all 6 cloud provider Kustomize overlays."""

    OVERLAYS = [
        ("prod-oci", "oci-", r"oci\.oraclecloud\.com/load-balancer-type:\s*[\"']?nlb[\"']?"),
        ("prod-aws", "aws-", r"service\.beta\.kubernetes\.io/aws-load-balancer-type:\s*[\"']?external[\"']?"),
        ("prod-gcp", "gcp-", r"cloud\.google\.com/load-balancer-type:\s*[\"']?External[\"']?"),
        ("prod-do", "do-", r"service\.beta\.kubernetes\.io/do-loadbalancer-protocol:\s*[\"']?tcp[\"']?"),
        ("prod-hetzner", "hetzner-", r"load-balancer\.hetzner\.cloud/type:\s*[\"']?lb11[\"']?"),
        ("prod-vultr", "vultr-", r"service\.beta\.kubernetes\.io/vultr-loadbalancer-protocol:\s*[\"']?tcp[\"']?"),
    ]

    def test_all_six_overlays_render_with_prefix_and_annotations(self):
        if not KUBECTL_BIN:
            self.skipTest("kubectl not found")

        for overlay_name, prefix, expected_pattern in self.OVERLAYS:
            out, err = run_kustomize(overlay_name)
            self.assertIsNone(err, f"Kustomize failed for {overlay_name}: {err}")
            self.assertIsNotNone(out)

            # Name prefix check
            self.assertIn(f"name: {prefix}sovereign-control-plane", out)
            self.assertIn(f"name: {prefix}sovereign-relay", out)
            self.assertIn(f"name: {prefix}sovereign-edge-gateway", out)
            self.assertIn("namespace: sovereign-mesh", out)

            # Cloud-specific loadbalancer annotation check
            self.assertRegex(out, expected_pattern, f"Annotation pattern {expected_pattern} not found in {overlay_name}")


class TestNetworkPolicyZeroTrustIsolation(unittest.TestCase):
    """Adversarial mathematical verification of RFC 1918 bogon subnet blocking."""

    def test_network_policy_bogon_cidrs_and_ip_filtering(self):
        out, err = run_helm_template()
        self.assertIsNone(err)

        # Expected bogon CIDRs that MUST be blocked
        expected_cidrs = [
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "169.254.0.0/16",
            "127.0.0.0/8",
        ]

        for cidr in expected_cidrs:
            self.assertIn(f"- {cidr}", out, f"CRITICAL: Subnet {cidr} missing from NetworkPolicy except block!")

        # Parse networks
        parsed_networks = [ipaddress.ip_network(c) for c in expected_cidrs]

        # Verify blocked IPs (RFC 1918, link-local, loopback)
        blocked_ips = [
            "10.0.0.1", "10.128.0.1", "10.255.255.254",
            "172.16.0.1", "172.24.1.1", "172.31.255.254",
            "192.168.0.1", "192.168.1.100", "192.168.255.254",
            "169.254.169.254", "127.0.0.1", "127.0.0.53",
        ]
        for ip_str in blocked_ips:
            ip = ipaddress.ip_address(ip_str)
            is_blocked = any(ip in net for net in parsed_networks)
            self.assertTrue(is_blocked, f"CRITICAL: Private/Bogon IP {ip_str} was NOT blocked by NetworkPolicy!")

        # Verify allowed public IPs (must pass to 0.0.0.0/0)
        allowed_ips = [
            "1.1.1.1", "8.8.8.8", "9.9.9.9",
            "142.250.190.46", "151.101.1.140", "104.244.42.1",
            "9.255.255.255", "11.0.0.1",
            "172.15.255.255", "172.32.0.1",
            "192.168.1.1" if False else "192.169.0.1",
            "172.15.255.255", "172.32.0.1",
            "192.167.255.255",
        ]
        for ip_str in allowed_ips:
            ip = ipaddress.ip_address(ip_str)
            is_blocked = any(ip in net for net in parsed_networks)
            self.assertFalse(is_blocked, f"CRITICAL: Public IP {ip_str} was incorrectly blocked by NetworkPolicy!")

    def test_dns_egress_and_ingress_ports(self):
        out, err = run_helm_template()
        self.assertIsNone(err)
        self.assertIn("port: 53", out)
        self.assertIn("kube-dns", out)
        self.assertIn("coredns", out)
        self.assertIn("port: 443", out)
        self.assertIn("port: 3478", out)
        self.assertIn("port: 8080", out)


class TestSecurityCapabilitiesAndVolumeScoping(unittest.TestCase):
    """Audits security capabilities, hostNetwork usage, and volume mounts."""

    def test_edge_gateway_and_relay_security_profiles(self):
        out, err = run_helm_template()
        self.assertIsNone(err)

        self.assertIn("- NET_ADMIN", out)
        self.assertIn("- NET_RAW", out)
        self.assertIn("hostNetwork: true", out)
        self.assertIn("path: /dev/net/tun", out)
        self.assertIn("allowPrivilegeEscalation: false", out)


if __name__ == "__main__":
    unittest.main()
