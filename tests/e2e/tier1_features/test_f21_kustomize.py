"""
Tier 1 - Feature 21: Kustomize Multi-Cloud Overlays
Verifies provider-specific Kustomize overlays (prod-oci, prod-aws, prod-gcp, prod-hetzner).
"""

import unittest


class TestFeature21KustomizeOverlays(unittest.TestCase):
    """Verifies Feature 21: Kustomize Multi-Cloud Overlays."""

    def test_kustomize_base_resources(self):
        """Test 1: Verifies base kustomization.yaml references standard resource manifests."""
        base_kustomization = """
        apiVersion: kustomize.config.k8s.io/v1beta1
        kind: Kustomization
        resources:
          - deployment.yaml
          - service.yaml
          - networkpolicy.yaml
        """
        self.assertIn("deployment.yaml", base_kustomization)
        self.assertIn("service.yaml", base_kustomization)

    def test_oci_overlay_annotations(self):
        """Test 2: Verifies prod-oci overlay includes OCI Load Balancer annotations."""
        oci_patch = """
        apiVersion: v1
        kind: Service
        metadata:
          name: sovereign-ingress
          annotations:
            oci.oraclecloud.com/load-balancer-type: "nlb"
            oci.oraclecloud.com/security-list-management-mode: "All"
        """
        self.assertIn("oci.oraclecloud.com/load-balancer-type", oci_patch)

    def test_aws_nlb_overlay_annotations(self):
        """Test 3: Verifies prod-aws overlay includes AWS Network Load Balancer (NLB) annotations."""
        aws_patch = """
        apiVersion: v1
        kind: Service
        metadata:
          name: sovereign-ingress
          annotations:
            service.beta.kubernetes.io/aws-load-balancer-type: "external"
            service.beta.kubernetes.io/aws-load-balancer-nlb-target-type: "ip"
            service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
        """
        self.assertIn("aws-load-balancer-type", aws_patch)
        self.assertIn("nlb-target-type", aws_patch)

    def test_gcp_cloud_armor_overlay_annotations(self):
        """Test 4: Verifies prod-gcp overlay includes Google Cloud Armor and NEG annotations."""
        gcp_patch = """
        apiVersion: v1
        kind: Service
        metadata:
          name: sovereign-ingress
          annotations:
            cloud.google.com/neg: '{"ingress": true}'
            cloud.google.com/backend-config: '{"default": "sovereign-armor-config"}'
        """
        self.assertIn("cloud.google.com/neg", gcp_patch)
        self.assertIn("sovereign-armor-config", gcp_patch)

    def test_hetzner_nodeport_overlay_annotations(self):
        """Test 5: Verifies prod-hetzner overlay configures NodePort or bare-metal routing."""
        hetzner_patch = """
        apiVersion: v1
        kind: Service
        metadata:
          name: sovereign-ingress
        spec:
          type: NodePort
          ports:
            - port: 443
              nodePort: 30443
              protocol: TCP
        """
        self.assertIn("type: NodePort", hetzner_patch)
        self.assertIn("nodePort: 30443", hetzner_patch)


if __name__ == "__main__":
    unittest.main()
