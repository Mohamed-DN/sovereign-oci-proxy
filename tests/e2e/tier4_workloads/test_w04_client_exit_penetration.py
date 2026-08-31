"""
Tier 4 - Workload 4: Untrusted Client Exit Node Containment & Penetration Stress
Features Exercised: F12 (Client Bridge), F13 (RFC 1918 Isolation), F8 (DoH Anti-Leak).
Complexity: High

Simulates a compromised client node attempting lateral penetration, port scanning,
cloud metadata extraction (169.254.169.254), SMTP spamming (port 25), and DNS exfiltration.
Verifies total isolation and 100% block rate across all attack vectors.
"""

import unittest
from tests.harness import MockClientExitNode, NodeGeoIP, RFC1918LeakDetector, DNSLeakDetector


class TestWorkload04ClientExitPenetration(unittest.TestCase):
    """Workload 4: Client Exit Node Penetration Containment Stress."""

    def test_untrusted_client_penetration_containment(self):
        geoip = NodeGeoIP("DE", "Frankfurt", 50.1, 8.6)
        exit_node = MockClientExitNode("exit-de-containment", geoip)

        # Attack Vector 1: Cloud Metadata Service Exfiltration Attempt (169.254.169.254)
        ok_meta, status_meta, _ = exit_node.handle_egress_request(
            client_node_id="malicious-client",
            dest_ip="169.254.169.254",
            dest_port=80,
            payload=b"GET /latest/meta-data/iam/security-credentials/ HTTP/1.1\r\n\r\n",
        )
        self.assertFalse(ok_meta)
        self.assertIn("DROP_RFC1918_BOGON", status_meta)

        # Attack Vector 2: Local LAN Lateral Movement (192.168.1.0/24 Subnet Scan)
        for last_octet in [1, 50, 100, 254]:
            target_ip = f"192.168.1.{last_octet}"
            ok_lan, status_lan, _ = exit_node.handle_egress_request(
                client_node_id="malicious-client",
                dest_ip=target_ip,
                dest_port=22,
            )
            self.assertFalse(ok_lan)
            self.assertIn("DROP_RFC1918_BOGON", status_lan)

        # Attack Vector 3: Corporate Internal Subnet (10.0.0.0/8)
        for host in ["10.0.0.1", "10.10.10.10", "10.254.254.254"]:
            ok_corp, status_corp, _ = exit_node.handle_egress_request(
                client_node_id="malicious-client",
                dest_ip=host,
                dest_port=445,
            )
            self.assertFalse(ok_corp)

        # Attack Vector 4: SMTP Spam Botnet Abuse (Port 25 against public mail servers)
        public_mail_servers = ["142.250.185.27", "205.251.193.0", "93.184.216.34"]
        for mail_ip in public_mail_servers:
            ok_smtp, status_smtp, _ = exit_node.handle_egress_request(
                client_node_id="malicious-client",
                dest_ip=mail_ip,
                dest_port=25,
            )
            self.assertFalse(ok_smtp)
            self.assertEqual(status_smtp, "DROP_RESTRICTED_PORT_25")

        # Attack Vector 5: NetBIOS / SMB Lateral Attacks (Ports 137, 138, 139, 445)
        for port in [137, 138, 139, 445]:
            ok_smb, status_smb, _ = exit_node.handle_egress_request(
                client_node_id="malicious-client",
                dest_ip="8.8.8.8",
                dest_port=port,
            )
            self.assertFalse(ok_smb)
            self.assertEqual(status_smb, f"DROP_RESTRICTED_PORT_{port}")

        # Attack Vector 6: Plaintext DNS Interception / Leak Check
        ok_dns, dns_msg = DNSLeakDetector.audit_dns_request("8.8.8.8", 53, "UDP")
        self.assertFalse(ok_dns)
        self.assertIn("Plaintext DNS", dns_msg)

        # Confirm 100% clean isolation via RFC 1918 detector
        leak_audit = RFC1918LeakDetector.audit_exit_node(exit_node)
        self.assertTrue(leak_audit.passed)
        self.assertEqual(len(leak_audit.violations), 0)


if __name__ == "__main__":
    unittest.main()
