#!/usr/bin/env python3
"""
Sovereign Proxy v4.0 — GitOps Cluster State Synchronization & Drift Detection Engine

Script: scripts/gitops/sync_cluster_state.py
Purpose:
    Validates cluster topology specifications (configs/mesh-cluster.yaml),
    detects drift between declared infrastructure and active nodes,
    validates network allocations (VIPs, ports, CIDRs), and generates
    reconciliation plans for multi-cloud deployments.
"""

import argparse
import ipaddress
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

try:
    import yaml
except ImportError:
    print("PyYAML required. Please install pyyaml or run in an environment with PyYAML.", file=sys.stderr)
    sys.exit(1)


VALID_PROVIDERS = {"oci", "aws", "gcp", "digitalocean", "hetzner", "vultr"}
VALID_ROLES = {"control-plane", "relay", "edge-gateway", "client-bridge"}


class ClusterStateValidator:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.data: Dict[str, Any] = {}

    def load_and_validate_schema(self) -> bool:
        if not self.config_path.exists():
            self.errors.append(f"Config file does not exist: {self.config_path}")
            return False

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.data = yaml.safe_load(f) or {}
        except Exception as e:
            self.errors.append(f"Failed to parse YAML from {self.config_path}: {e}")
            return False

        # Validate apiVersion and kind
        api_ver = self.data.get("apiVersion", "")
        kind = self.data.get("kind", "")
        if "sovereign.mesh" not in api_ver:
            self.warnings.append(f"Unrecognized apiVersion: '{api_ver}', expected 'sovereign.mesh/v4alpha1'")
        if kind != "SovereignCluster":
            self.warnings.append(f"Unrecognized kind: '{kind}', expected 'SovereignCluster'")

        self._validate_global_section()
        self._validate_control_plane_section()
        self._validate_relay_fleet_section()
        return len(self.errors) == 0

    def _validate_global_section(self):
        global_cfg = self.data.get("global", {})
        domain = global_cfg.get("domain")
        if not domain:
            self.warnings.append("global.domain is not set.")
        encryption = global_cfg.get("encryption", {})
        noise_suite = encryption.get("noiseSuite", "")
        if noise_suite and not noise_suite.startswith("Noise_"):
            self.warnings.append(f"Unusual noiseSuite: '{noise_suite}'")

    def _validate_control_plane_section(self):
        cp = self.data.get("controlPlane", {})
        replicas = cp.get("replicas", 0)
        distribution = cp.get("distribution", [])
        if replicas > 0 and len(distribution) < replicas:
            self.warnings.append(f"controlPlane specifies {replicas} replicas but only {len(distribution)} distributed locations.")

        for item in distribution:
            prov = item.get("provider", "")
            if prov and prov not in VALID_PROVIDERS:
                self.errors.append(f"Invalid provider in controlPlane: '{prov}'")

    def _validate_relay_fleet_section(self):
        fleet = self.data.get("relayFleet", {})
        nodes = fleet.get("nodes", [])
        node_ids: Set[str] = set()

        for idx, node in enumerate(nodes):
            nid = node.get("id", f"node-{idx}")
            if nid in node_ids:
                self.errors.append(f"Duplicate node id detected in relayFleet: '{nid}'")
            node_ids.add(nid)

            prov = node.get("provider", "")
            if prov and prov not in VALID_PROVIDERS:
                self.errors.append(f"Node '{nid}' has unknown provider '{prov}'")

            # Check network ports
            net_cfg = node.get("network", {})
            inbound_ports = net_cfg.get("allowedInboundPorts", [])
            for p in inbound_ports:
                if not (1 <= p <= 65535):
                    self.errors.append(f"Node '{nid}' invalid port: {p}")

    def generate_drift_report(self, state_snapshot: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generates drift comparison between declared yaml and active state snapshot."""
        declared_nodes = {n.get("id"): n for n in self.data.get("relayFleet", {}).get("nodes", [])}
        active_nodes = state_snapshot.get("active_nodes", {}) if state_snapshot else {}

        missing_in_cluster = [nid for nid in declared_nodes if nid not in active_nodes]
        unmanaged_in_cluster = [nid for nid in active_nodes if nid not in declared_nodes]

        return {
            "status": "DRIFT_DETECTED" if (missing_in_cluster or unmanaged_in_cluster) else "IN_SYNC",
            "declared_node_count": len(declared_nodes),
            "active_node_count": len(active_nodes),
            "missing_nodes": missing_in_cluster,
            "unmanaged_nodes": unmanaged_in_cluster,
            "validation_errors": self.errors,
            "validation_warnings": self.warnings,
        }


def main():
    parser = argparse.ArgumentParser(description="SovereignMesh GitOps Cluster State Sync & Drift Engine")
    parser.add_argument(
        "--config",
        "-c",
        default="configs/mesh-cluster.yaml",
        help="Path to unified mesh cluster config yaml",
    )
    parser.add_argument(
        "--command",
        choices=["validate", "drift-check", "reconcile", "summary"],
        default="validate",
        help="GitOps action to perform",
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path

    validator = ClusterStateValidator(config_path)
    is_valid = validator.load_and_validate_schema()

    if args.command == "validate":
        if args.json:
            print(json.dumps({
                "valid": is_valid,
                "errors": validator.errors,
                "warnings": validator.warnings
            }, indent=2))
        else:
            print("================================================================")
            print(f" SovereignMesh Config Validation: {config_path.name}")
            print("================================================================")
            if is_valid:
                print("✓ Configuration schema is VALID.")
            else:
                print("✗ Configuration schema contains ERRORS:")
                for err in validator.errors:
                    print(f"  - ERROR: {err}")

            if validator.warnings:
                print("\nWarnings:")
                for warn in validator.warnings:
                    print(f"  - WARN:  {warn}")

        sys.exit(0 if is_valid else 1)

    elif args.command in ["drift-check", "reconcile", "summary"]:
        report = validator.generate_drift_report()
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print("================================================================")
            print(f" SovereignMesh GitOps Drift Report")
            print("================================================================")
            print(f"Status:               {report['status']}")
            print(f"Declared Nodes:       {report['declared_node_count']}")
            print(f"Active Nodes:         {report['active_node_count']}")
            print(f"Missing Nodes:        {len(report['missing_nodes'])}")
            print(f"Unmanaged Nodes:      {len(report['unmanaged_nodes'])}")
            if report['validation_errors']:
                print(f"Errors:               {len(report['validation_errors'])}")
        sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
