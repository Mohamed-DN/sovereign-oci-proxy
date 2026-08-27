"""
Tier 5 - Adversarial Suite 1: Anti-Replay Sliding Window Stress & Replay Attack Fuzzing
Tests 64-bit sliding window anti-replay protection under reordered packets, duplicates, and deep replay attacks.
"""

import unittest
import random
import time


class AntiReplaySlidingWindow:
    def __init__(self, size: int = 1024):
        self.size = size
        self.max_seq = 0
        self.seen = set()

    def check_and_add(self, seq: int) -> bool:
        if self.max_seq == 0 and len(self.seen) == 0:
            self.max_seq = seq
            self.seen.add(seq)
            return True
        if seq > self.max_seq:
            diff = seq - self.max_seq
            if diff >= self.size:
                self.seen.clear()
            else:
                self.seen = {s for s in self.seen if (seq - s) < self.size}
            self.max_seq = seq
            self.seen.add(seq)
            return True
        diff = self.max_seq - seq
        if diff >= self.size:
            return False  # Too old
        if seq in self.seen:
            return False  # Replay / Duplicate
        self.seen.add(seq)
        return True


class TestAdversarial01AntiReplayWindow(unittest.TestCase):
    """Adversarial anti-replay window stress tests."""

    def test_monotonic_sequence_and_duplicate_rejection(self):
        window = AntiReplaySlidingWindow(size=1024)
        for seq in range(1, 5000):
            self.assertTrue(window.check_and_add(seq), f"Fresh sequence {seq} should be accepted")
            # Immediate replay must be rejected
            self.assertFalse(window.check_and_add(seq), f"Duplicate sequence {seq} must be rejected")

    def test_out_of_order_within_window(self):
        window = AntiReplaySlidingWindow(size=1024)
        window.check_and_add(2000)
        # Sequence numbers inside window [977 .. 1999] in random order
        in_window_seqs = list(range(1500, 2000))
        random.shuffle(in_window_seqs)

        for seq in in_window_seqs:
            self.assertTrue(window.check_and_add(seq), f"In-window out-of-order {seq} should be accepted")
            # Second attempt is duplicate
            self.assertFalse(window.check_and_add(seq))

    def test_stale_packet_beyond_window_rejection(self):
        window = AntiReplaySlidingWindow(size=1024)
        window.check_and_add(10000)
        # Packets older than 10000 - 1024 = 8976 must be rejected
        for old_seq in [1, 500, 1000, 5000, 8975]:
            self.assertFalse(window.check_and_add(old_seq), f"Stale sequence {old_seq} must be rejected")

    def test_large_gap_leap_forward(self):
        window = AntiReplaySlidingWindow(size=1024)
        window.check_and_add(100)
        # Leap forward by 1,000,000
        self.assertTrue(window.check_and_add(1000100))
        # Now 100 is completely out of window
        self.assertFalse(window.check_and_add(100))


if __name__ == "__main__":
    unittest.main()
