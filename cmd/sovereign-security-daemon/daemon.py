#!/usr/bin/env python3
"""
Sovereign Security Daemon - Python Reference Implementation & Test Runner
Location: cmd/sovereign-security-daemon/daemon.py
Provides async rate-limited honeypot defense, threat scoring, and CIDR protection.
"""

import argparse
import asyncio
import ipaddress
import json
import logging
import math
import os
import signal
import sys
import time
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [SecurityDaemon] %(message)s")
logger = logging.getLogger("sovereign-security-daemon")

BANNER = (
    b"HTTP/1.1 200 OK\r\n"
    b"Server: nginx/1.26.1\r\n"
    b"Content-Type: text/html\r\n"
    b"Content-Length: 52\r\n"
    b"Connection: close\r\n\r\n"
    b"<html><body><h1>System Operational</h1></body></html>\r\n"
)

DEFAULT_WHITELIST = [
    "127.0.0.0/8",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "100.64.0.0/10",
    "169.254.0.0/16",
    "224.0.0.0/4",
    "1.1.1.1/32",
    "1.0.0.1/32",
    "8.8.8.8/32",
    "8.8.4.4/32",
    "9.9.9.9/32",
]


class WhitelistManager:
    def __init__(self, cidrs: List[str]):
        self.networks = []
        for raw in cidrs:
            raw = raw.strip()
            if not raw:
                continue
            try:
                if "/" not in raw:
                    raw = f"{raw}/32" if ":" not in raw else f"{raw}/128"
                self.networks.append(ipaddress.ip_network(raw, strict=False))
            except ValueError as e:
                logger.warning(f"Invalid whitelist entry '{raw}': {e}")

    def is_whitelisted(self, ip_str: str) -> bool:
        try:
            ip = ipaddress.ip_address(ip_str)
            if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
                return True
            for net in self.networks:
                if ip in net:
                    return True
        except ValueError:
            return True
        return False


class TokenBucket:
    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def allow(self, cost: float = 1.0) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.last_refill = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


class DualTokenBucketLimiter:
    def __init__(self, ip_cap: int = 5, ip_refill: float = 1.0, subnet_cap: int = 20, subnet_refill: float = 5.0):
        self.ip_cap = float(ip_cap)
        self.ip_refill = ip_refill
        self.subnet_cap = float(subnet_cap)
        self.subnet_refill = subnet_refill
        self.ip_buckets: Dict[str, TokenBucket] = {}
        self.subnet_buckets: Dict[str, TokenBucket] = {}

    def _get_subnet_key(self, ip_str: str) -> str:
        try:
            ip = ipaddress.ip_address(ip_str)
            if ip.version == 4:
                return str(ipaddress.ip_network(f"{ip_str}/24", strict=False))
            else:
                return str(ipaddress.ip_network(f"{ip_str}/48", strict=False))
        except ValueError:
            return "unknown"

    def allow(self, ip_str: str) -> bool:
        subnet_key = self._get_subnet_key(ip_str)

        if ip_str not in self.ip_buckets:
            self.ip_buckets[ip_str] = TokenBucket(self.ip_cap, self.ip_refill)
        if subnet_key not in self.subnet_buckets:
            self.subnet_buckets[subnet_key] = TokenBucket(self.subnet_cap, self.subnet_refill)

        ip_ok = self.ip_buckets[ip_str].allow(1.0)
        subnet_ok = self.subnet_buckets[subnet_key].allow(1.0)
        return ip_ok and subnet_ok


class ThreatScorer:
    def __init__(self, ban_threshold: int = 100, half_life_seconds: float = 3600.0):
        self.ban_threshold = float(ban_threshold)
        self.decay_lambda = math.log(2) / max(1.0, half_life_seconds)
        self.scores: Dict[str, Tuple[float, float]] = {}  # ip -> (score, last_time)

    def record_threat(self, ip_str: str, points: float) -> Tuple[float, bool]:
        now = time.time()
        if ip_str in self.scores:
            old_score, last_time = self.scores[ip_str]
            elapsed = now - last_time
            decayed = old_score * math.exp(-self.decay_lambda * elapsed)
            new_score = decayed + points
        else:
            new_score = points

        self.scores[ip_str] = (new_score, now)
        return new_score, new_score >= self.ban_threshold

    def get_score(self, ip_str: str) -> float:
        if ip_str not in self.scores:
            return 0.0
        old_score, last_time = self.scores[ip_str]
        elapsed = time.time() - last_time
        return old_score * math.exp(-self.decay_lambda * elapsed)


class MockFirewallDriver:
    def __init__(self):
        self.banned: Dict[str, Tuple[float, str]] = {}  # ip -> (expires_at, reason)

    async def ban(self, ip_str: str, duration_sec: float, reason: str):
        expires_at = time.time() + duration_sec
        self.banned[ip_str] = (expires_at, reason)
        logger.info(f"[Firewall/Mock] BANNED {ip_str} for {duration_sec}s: {reason}")

    async def is_banned(self, ip_str: str) -> bool:
        if ip_str in self.banned:
            expires_at, _ = self.banned[ip_str]
            if time.time() < expires_at:
                return True
            del self.banned[ip_str]
        return False


class SecurityDaemon:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080, dry_run: bool = False):
        self.host = host
        self.port = port
        self.dry_run = dry_run
        self.whitelist = WhitelistManager(DEFAULT_WHITELIST)
        self.limiter = DualTokenBucketLimiter()
        self.scorer = ThreatScorer(ban_threshold=100, half_life_seconds=3600.0)
        self.firewall = MockFirewallDriver()
        self.server = None

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer = writer.get_extra_info("peername")
        ip_str = peer[0] if peer else "0.0.0.0"

        try:
            # Whitelist check
            if self.whitelist.is_whitelisted(ip_str):
                writer.write(BANNER)
                await writer.drain()
                return

            # Rate limit check
            if not self.limiter.allow(ip_str):
                return

            # Send fake banner
            writer.write(BANNER)
            await writer.drain()

            # Threat score
            score, should_ban = self.scorer.record_threat(ip_str, 35.0)
            if should_ban:
                if not await self.firewall.is_banned(ip_str):
                    await self.firewall.ban(ip_str, 86400, f"Honeypot score {score:.1f} >= 100")
        except Exception as e:
            logger.debug(f"Error handling connection from {ip_str}: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self):
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        logger.info(f"Honeypot listener active on {self.host}:{self.port}")
        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Security daemon stopped.")


def main():
    parser = argparse.ArgumentParser(description="Sovereign Proxy Active Defense Daemon")
    parser.add_argument("--port", type=int, default=8080, help="Honeypot port")
    parser.add_argument("--host", default="0.0.0.0", help="Listen address")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    args = parser.parse_args()

    daemon = SecurityDaemon(host=args.host, port=args.port, dry_run=args.dry_run)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(daemon.start())
    except KeyboardInterrupt:
        loop.run_until_complete(daemon.stop())


if __name__ == "__main__":
    main()
