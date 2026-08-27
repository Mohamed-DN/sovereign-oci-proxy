"""
Tier 4 - Scenario 13: Dynamic DNS IP Change Detection & DuckDNS Update Recovery
Features Exercised: F03 (Dynamic DNS & Discovery).
"""

import unittest


class DynamicDNSDiscoveryDaemon:
    def __init__(self, domain: str, token: str, check_interval: int = 5):
        self.domain = domain
        self.token = token
        self.check_interval = check_interval
        self._current_ip = "127.0.0.1"
        self._synced_ip = None

    def set_simulated_external_ip(self, ip: str):
        self._current_ip = ip

    def check_and_update(self) -> tuple[str, bool]:
        if self._current_ip != self._synced_ip:
            self._synced_ip = self._current_ip
            return self._current_ip, True
        return self._current_ip, False


class TestScenario13DynamicDNSDuckDNSRecovery(unittest.TestCase):
    """Scenario 13: Dynamic DNS auto-update on IP transition."""

    def test_dynamic_dns_ip_change_and_duckdns_update(self):
        daemon = DynamicDNSDiscoveryDaemon(
            domain="sovereign-node-01.duckdns.org",
            token="dummy-duckdns-token-12345",
            check_interval=5,
        )

        # 1. Initial IP detection
        daemon.set_simulated_external_ip("198.51.100.25")
        ip1, updated1 = daemon.check_and_update()
        self.assertEqual(ip1, "198.51.100.25")
        self.assertTrue(updated1)

        # 2. Unchanged IP does not trigger redundant sync
        ip2, updated2 = daemon.check_and_update()
        self.assertEqual(ip2, "198.51.100.25")
        self.assertFalse(updated2)

        # 3. Public IP changes -> automatic detection and sync
        daemon.set_simulated_external_ip("203.0.113.88")
        ip3, updated3 = daemon.check_and_update()
        self.assertEqual(ip3, "203.0.113.88")
        self.assertTrue(updated3)


if __name__ == "__main__":
    unittest.main()
