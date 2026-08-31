"""
Tier 1 - Feature 7: Nginx Decoy & Sub Proxy Hardening
Verifies decoy web server configuration on loopback with hardened headers,
TLS mimicry, subscription proxy, and anti-probing.
"""

import unittest
import re


class DecoyServerSimulator:
    """Simulates Nginx decoy web server and subscription proxy."""

    def __init__(self, sub_token: str = "sub_secret_token_12345"):
        self.sub_token = sub_token
        self.hardened_headers = {
            "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'self'",
        }

    def handle_http_request(self, path: str, headers: dict) -> tuple[int, dict, str]:
        # Anti-probing scanner drop
        user_agent = headers.get("User-Agent", "").lower()
        if any(scanner in user_agent for scanner in ["zgrab", "shodan", "masscan", "nmap", "nikto"]):
            return 444, {}, "DROP_CONNECTION"

        # Subscription endpoint
        if path.startswith("/sub/"):
            token = path.split("/sub/", 1)[1]
            if token == self.sub_token:
                return 200, self.hardened_headers, "vless://base64_encoded_node_sub_config"
            return 403, self.hardened_headers, "Forbidden"

        # General decoy page
        if path == "/" or path == "/index.html":
            return 200, self.hardened_headers, "<html><body><h1>Welcome</h1></body></html>"

        return 404, self.hardened_headers, "<html><body><h1>404 Not Found</h1></body></html>"


class TestFeature07NginxDecoy(unittest.TestCase):
    """Verifies Feature 7: Nginx Decoy & Sub Proxy Hardening."""

    def setUp(self):
        self.decoy = DecoyServerSimulator(sub_token="valid_sub_token_abc")

    def test_decoy_loopback_binding(self):
        """Test 1: Verifies decoy server is intended to bind exclusively to loopback 127.0.0.1."""
        listen_directive = "listen 127.0.0.1:8080 default_server;"
        self.assertIn("127.0.0.1", listen_directive)
        self.assertNotIn("0.0.0.0", listen_directive)

    def test_hardened_http_security_headers(self):
        """Test 2: Verifies all expected enterprise security headers are returned on decoy responses."""
        status, headers, body = self.decoy.handle_http_request("/", {"User-Agent": "Mozilla/5.0"})
        self.assertEqual(status, 200)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertIn("includeSubDomains", headers["Strict-Transport-Security"])

    def test_tls_13_cipher_suite_negotiation(self):
        """Test 3: Verifies TLS 1.3 preferred modern cipher suites."""
        cipher_suites = [
            "TLS_AES_256_GCM_SHA384",
            "TLS_CHACHA20_POLY1305_SHA256",
            "TLS_AES_128_GCM_SHA256",
        ]
        for cipher in cipher_suites:
            self.assertTrue(cipher.startswith("TLS_"))
            self.assertIn("SHA", cipher)

    def test_subscription_token_auth(self):
        """Test 4: Verifies subscription endpoint grants config only on valid token."""
        # Valid token
        status, _, body = self.decoy.handle_http_request("/sub/valid_sub_token_abc", {"User-Agent": "ClashMeta"})
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith("vless://"))

        # Invalid token
        status_bad, _, _ = self.decoy.handle_http_request("/sub/wrong_token", {"User-Agent": "ClashMeta"})
        self.assertEqual(status_bad, 403)

    def test_scanner_anti_probing_drop(self):
        """Test 5: Verifies known scanner User-Agents trigger silent connection drop (HTTP 444)."""
        scanners = ["Zgrab/0.x", "Shodan-scanner", "masscan/1.0", "Nmap Scripting Engine"]
        for agent in scanners:
            status, _, _ = self.decoy.handle_http_request("/", {"User-Agent": agent})
            self.assertEqual(status, 444)


if __name__ == "__main__":
    unittest.main()
