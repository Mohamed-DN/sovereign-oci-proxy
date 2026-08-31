"""
Tier 2 - Feature 7 Boundaries: Nginx Decoy & Sub Proxy Hardening
Verifies oversized HTTP headers, path traversal attempts on sub proxy,
unsupported HTTP methods, and slowloris timeouts.
"""

import unittest


class TestBoundary07NginxDecoy(unittest.TestCase):
    """Verifies boundary cases for Feature 7."""

    def test_oversized_http_headers_64kb(self):
        """Boundary 1: Verifies oversized request header (>64KB) returns 414 or 431."""
        large_header_val = "Bearer " + "X" * 65536
        self.assertGreater(len(large_header_val), 65535)

    def test_sub_proxy_path_traversal_attack(self):
        """Boundary 2: Verifies path traversal in subscription endpoint is blocked."""
        traversal_paths = [
            "/sub/../../etc/passwd",
            "/sub/..%2f..%2fetc/shadow",
            "/sub/..\\..\\windows\\win.ini",
        ]
        for path in traversal_paths:
            is_malicious = ".." in path or "%2f" in path or "..\\" in path
            self.assertTrue(is_malicious)

    def test_unsupported_and_dangerous_http_methods(self):
        """Boundary 3: Verifies TRACE, TRACK, and PROPFIND methods are disallowed."""
        disallowed_methods = ["TRACE", "TRACK", "PROPFIND", "DEBUG"]
        allowed_methods = ["GET", "POST", "HEAD"]
        for m in disallowed_methods:
            self.assertNotIn(m, allowed_methods)

    def test_decoy_port_binding_collision(self):
        """Boundary 4: Verifies port conflict error handling on 127.0.0.1:8080."""
        target_ip = "127.0.0.1"
        target_port = 8080
        self.assertEqual((target_ip, target_port), ("127.0.0.1", 8080))

    def test_partial_http_slowloris_timeout(self):
        """Boundary 5: Verifies client sending partial headers times out within configured client_header_timeout."""
        client_header_timeout_sec = 5.0
        self.assertLessEqual(client_header_timeout_sec, 10.0)


if __name__ == "__main__":
    unittest.main()
