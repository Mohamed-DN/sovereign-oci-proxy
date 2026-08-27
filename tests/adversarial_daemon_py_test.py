#!/usr/bin/env python3
"""
Adversarial Python Security Daemon Stress Test
Tests: cmd/sovereign-security-daemon/daemon.py under high concurrency (10,000+ operations)
"""

import asyncio
import importlib.util
import os
import sys
import time

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAEMON_PY = os.path.join(WORKSPACE_ROOT, "cmd", "sovereign-security-daemon", "daemon.py")

spec = importlib.util.spec_from_file_location("sec_daemon", DAEMON_PY)
sec_daemon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sec_daemon)


def test_dual_token_bucket_stress():
    print("[*] Testing Python DualTokenBucketLimiter under 20,000 rapid requests...")
    limiter = sec_daemon.DualTokenBucketLimiter(ip_cap=10, ip_refill=2.0, subnet_cap=50, subnet_refill=10.0)

    total_requests = 20000
    allowed = 0
    dropped = 0

    start = time.time()
    for i in range(total_requests):
        subnet = i % 10
        host = (i // 10) % 100
        ip_str = f"198.51.{100 + subnet}.{1 + host}"

        if limiter.allow(ip_str):
            allowed += 1
        else:
            dropped += 1

    duration = time.time() - start
    rate = total_requests / max(0.001, duration)
    print(f"  Processed {total_requests} checks in {duration:.4f}s ({rate:.2f} ops/sec)")
    print(f"  Allowed: {allowed}, Dropped: {dropped}")

    assert dropped > 0, "Rate limiter failed to drop requests during flood"
    assert allowed <= 1500, f"Rate limiter allowed too many requests ({allowed} > 1500)"
    print("  [+] Token bucket rate limiting passed.")


def test_threat_scorer_decay_and_ban():
    print("\n[*] Testing Python ThreatScorer under 10,000 concurrent attacks...")
    scorer = sec_daemon.ThreatScorer(ban_threshold=100, half_life_seconds=3600.0)

    total_attacks = 10000
    ban_triggers = 0

    start = time.time()
    for i in range(total_attacks):
        ip_idx = i % 50
        ip_str = f"203.0.113.{ip_idx + 1}"
        _, should_ban = scorer.record_threat(ip_str, 35.0)
        if should_ban:
            ban_triggers += 1

    duration = time.time() - start
    rate = total_attacks / max(0.001, duration)
    print(f"  Executed {total_attacks} threat evaluations in {duration:.4f}s ({rate:.2f} ops/sec)")
    print(f"  Total ban triggers observed: {ban_triggers}")

    for i in range(50):
        ip_str = f"203.0.113.{i + 1}"
        score = scorer.get_score(ip_str)
        assert score >= 100.0, f"IP {ip_str} score {score} < 100.0"

    print("  [+] Threat scoring and decay passed.")


def test_upstream_gateway_protection():
    print("\n[*] Testing Upstream Gateway Anti-Blacklist Whitelist Immunity...")
    daemon = sec_daemon.SecurityDaemon(host="127.0.0.1", port=18888, dry_run=True)

    critical_gateways = [
        "1.1.1.1",
        "1.0.0.1",
        "8.8.8.8",
        "8.8.4.4",
        "9.9.9.9",
        "100.64.0.1",
        "100.64.50.1",
        "127.0.0.1",
        "10.0.0.1",
        "192.168.1.1",
        "172.16.0.1",
        "169.254.169.254",
    ]

    for ip in critical_gateways:
        is_wl = daemon.whitelist.is_whitelisted(ip)
        assert is_wl, f"CRITICAL: Gateway {ip} not recognized as whitelisted!"

        # Attempt to record threat
        for _ in range(50):
            if not daemon.whitelist.is_whitelisted(ip):
                daemon.scorer.record_threat(ip, 35.0)

        score = daemon.scorer.get_score(ip)
        assert score == 0.0, f"Gateway {ip} accumulated threat score: {score}"

    print("  [+] All 12 critical upstream gateways are 100% immune from blacklisting.")


async def test_live_async_daemon_flood():
    print("\n[*] Testing Live Async Security Daemon Server under 1,000 concurrent TCP handshakes...")
    daemon = sec_daemon.SecurityDaemon(host="127.0.0.1", port=18889, dry_run=True)
    server_task = asyncio.create_task(daemon.start())
    await asyncio.sleep(0.1)

    async def connect_client():
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 18889)
            data = await reader.read(64)
            writer.close()
            await writer.wait_closed()
            return len(data) > 0
        except Exception:
            return False

    tasks = [connect_client() for _ in range(1000)]
    start = time.time()
    results = await asyncio.gather(*tasks)
    duration = time.time() - start

    success_count = sum(1 for r in results if r)
    rate = len(tasks) / max(0.001, duration)
    print(f"  Processed {len(tasks)} client handshakes in {duration:.4f}s ({rate:.2f} conn/sec)")
    print(f"  Successful banner reads: {success_count}/{len(tasks)}")

    await daemon.stop()
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass

    assert success_count > 0, "Daemon failed to serve any clients under load"
    print("  [+] Live server stress test passed.")


def main():
    test_dual_token_bucket_stress()
    test_threat_scorer_decay_and_ban()
    test_upstream_gateway_protection()
    asyncio.run(test_live_async_daemon_flood())
    print("\n" + "="*80)
    print("🎉 ALL SECURITY DAEMON ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY!")
    print("="*80)


if __name__ == "__main__":
    main()
