"""
Tier 3 - Scenario 5: Honeypot Async Rate Limiter & Nginx Decoy Fallback (F2 + F7)
Verifies scanner detection on Nginx decoy feeding threat score into async ban daemon.
"""

import unittest
from tests.e2e.tier1_features.test_f02_honeypot_dos import AsyncThreatScorer
from tests.e2e.tier1_features.test_f07_nginx_decoy import DecoyServerSimulator


class TestScenario05HoneypotWithDecoy(unittest.TestCase):
    """Pairwise Integration: F2 (Honeypot DoS) + F7 (Nginx Decoy)."""

    def test_scanner_detection_triggers_async_ban(self):
        scorer = AsyncThreatScorer(ban_threshold=100)
        decoy = DecoyServerSimulator()
        scanner_ip = "198.51.100.222"

        # Scanner sends probe
        status, _, _ = decoy.handle_http_request("/", {"User-Agent": "Shodan-scanner"})
        self.assertEqual(status, 444)

        # Record threat event
        if status == 444:
            scorer.record_threat_event(scanner_ip, 100)

        scorer.process_pending_events()
        self.assertTrue(scorer.is_ip_banned(scanner_ip))


if __name__ == "__main__":
    unittest.main()
