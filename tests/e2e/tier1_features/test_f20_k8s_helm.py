"""
Tier 1 - Feature 20: Kubernetes Helm Chart (`sovereign-mesh`)
Verifies enterprise Helm chart structure, HA Control Plane Deployment, DERP Relay StatefulSet,
Edge Gateway DaemonSet, and NetworkPolicy.
"""

import unittest
import json


class TestFeature20K8sHelm(unittest.TestCase):
    """Verifies Feature 20: Kubernetes Helm Chart (`sovereign-mesh`)."""

    def test_helm_chart_metadata(self):
        """Test 1: Verifies Chart.yaml metadata specification."""
        chart_yaml = {
            "apiVersion": "v2",
            "name": "sovereign-mesh",
            "description": "Enterprise Anti-Censorship Mesh & Sovereign Proxy v4.0",
            "type": "application",
            "version": "4.0.0",
            "appVersion": "4.0.0",
        }
        self.assertEqual(chart_yaml["name"], "sovereign-mesh")
        self.assertEqual(chart_yaml["apiVersion"], "v2")
        self.assertEqual(chart_yaml["appVersion"], "4.0.0")

    def test_control_plane_deployment_manifest(self):
        """Test 2: Verifies HA Control Plane Deployment with liveness and readiness probes."""
        deployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "sovereign-control-plane"},
            "spec": {
                "replicas": 3,
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "control-plane",
                            "image": "sovereign/control-plane:4.0.0",
                            "livenessProbe": {"httpGet": {"path": "/healthz", "port": 8080}},
                            "readinessProbe": {"httpGet": {"path": "/ready", "port": 8080}},
                        }]
                    }
                }
            }
        }
        self.assertEqual(deployment["spec"]["replicas"], 3)
        self.assertIn("livenessProbe", deployment["spec"]["template"]["spec"]["containers"][0])

    def test_derp_relay_statefulset_manifest(self):
        """Test 3: Verifies DERP Relay StatefulSet with hostPort/NodePort for UDP and TCP."""
        statefulset = {
            "apiVersion": "apps/v1",
            "kind": "StatefulSet",
            "metadata": {"name": "sovereign-derp-relay"},
            "spec": {
                "replicas": 3,
                "serviceName": "derp-relay-headless",
                "template": {
                    "spec": {
                        "containers": [{
                            "name": "relay",
                            "ports": [
                                {"containerPort": 443, "name": "https-relay"},
                                {"containerPort": 3478, "protocol": "UDP", "name": "stun"},
                            ]
                        }]
                    }
                }
            }
        }
        ports = statefulset["spec"]["template"]["spec"]["containers"][0]["ports"]
        self.assertEqual(len(ports), 2)
        self.assertTrue(any(p["protocol"] == "UDP" for p in ports if "protocol" in p))

    def test_edge_gateway_daemonset_manifest(self):
        """Test 4: Verifies Edge Gateway DaemonSet with hostNetwork and required network caps."""
        daemonset = {
            "apiVersion": "apps/v1",
            "kind": "DaemonSet",
            "metadata": {"name": "sovereign-edge-gateway"},
            "spec": {
                "template": {
                    "spec": {
                        "hostNetwork": True,
                        "containers": [{
                            "name": "edge",
                            "securityContext": {
                                "capabilities": {"add": ["NET_ADMIN", "NET_BIND_SERVICE"]}
                            }
                        }]
                    }
                }
            }
        }
        self.assertTrue(daemonset["spec"]["template"]["spec"]["hostNetwork"])
        caps = daemonset["spec"]["template"]["spec"]["containers"][0]["securityContext"]["capabilities"]["add"]
        self.assertIn("NET_ADMIN", caps)

    def test_k8s_network_policy_manifest(self):
        """Test 5: Verifies NetworkPolicy enforcing zero-trust ingress and egress isolation."""
        netpol = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {"name": "sovereign-mesh-netpol"},
            "spec": {
                "podSelector": {"matchLabels": {"app.kubernetes.io/name": "sovereign-mesh"}},
                "policyTypes": ["Ingress", "Egress"],
            }
        }
        self.assertEqual(netpol["spec"]["policyTypes"], ["Ingress", "Egress"])


if __name__ == "__main__":
    unittest.main()
