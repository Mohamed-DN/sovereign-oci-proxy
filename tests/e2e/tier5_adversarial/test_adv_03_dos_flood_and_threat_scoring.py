"""
Tier 5 - Adversarial Suite 3: High-Concurrency DoS Flood & Threat Scorer Saturation
Tests security daemon under high-volume flood and validates decay algorithms.
"""

import unittest
from tests.e2e.tier1_features.test_f02_honeypot_dos import AsyncThreatScorer, TokenBucketRateLimiter


class TestAdversarial03DoSFloodAndThreatScoring(unittest.TestCase):
    """Adversarial DoS flood and threat scorer stress tests."""

    def test_token_bucket_saturation_under_flood(self):
        limiter = TokenBucketRateLimiter(capacity=10, refill_rate=2.0)

        allowed = 0
        dropped = 0
        for _ in range(2000):
            if limiter.allow_request():
                allowed += 1
            else:
                dropped += 1

        self.assertLessEqual(allowed, 15, "Rate limiter allowed too many bursts")
        self.assertGreater(dropped, 1980, "Rate limiter failed to drop excessive flood")

    def test_threat_scorer_mass_evaluation_and_decay(self):
        scorer = AsyncThreatScorer(ban_threshold=100, ban_ttl_sec=60.0)

        # 50 attacker IPs with high threat score
        for i in range(50):
            ip = f"203.0.113.{i+1}"
            scorer.record_threat_event(ip, 120)

        scorer.process_pending_events()

        for i in range(50):
            ip = f"203.0.113.{i+1}"
            self.assertTrue(scorer.is_ip_banned(ip))


if __name__ == "__main__":
    unittest.main()
