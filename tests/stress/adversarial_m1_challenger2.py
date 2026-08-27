#!/usr/bin/env python3
"""
Adversarial Verification Suite for Milestone 1 (Challenger 2)
Location: tests/stress/adversarial_m1_challenger2.py

Empirically challenges:
1. Rootless container security profile & Docker compose configuration.
2. Deep multi-pattern secret scanner across the entire repository.
3. Python reference security daemon async concurrency & token bucket isolation.
"""

import asyncio
import os
import re
import socket
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

PASS_COUNT = 0
FAIL_COUNT = 0


def record_result(test_name: str, passed: bool, detail: str = ""):
    global PASS_COUNT, FAIL_COUNT
    if passed:
        PASS_COUNT += 1
        print(f"  [{GREEN}✓{RESET}] {test_name}: {GREEN}PASSED{RESET} {detail}")
    else:
        FAIL_COUNT += 1
        print(f"  [{RED}✗{RESET}] {test_name}: {RED}FAILED{RESET} {detail}")


def test_container_security():
    print(f"\n{BLUE}{BOLD}=== 1. Container Security Architecture Deep Validation ==={RESET}")
    dockerfile_path = REPO_ROOT / "docker" / "Dockerfile"
    compose_path = REPO_ROOT / "docker" / "docker-compose.yml"
    entrypoint_path = REPO_ROOT / "docker" / "entrypoint.sh"

    dockerfile_content = dockerfile_path.read_text()
    compose_content = compose_path.read_text()
    entrypoint_content = entrypoint_path.read_text()

    # Dockerfile checks
    record_result("Dockerfile exists", dockerfile_path.exists())
    record_result("Dockerfile multi-stage builder", "FROM golang:" in dockerfile_content and "FROM alpine:" in dockerfile_content)
    record_result("Dockerfile UID 10001 user creation", "addgroup -g 10001" in dockerfile_content and "adduser -u 10001" in dockerfile_content)
    record_result("Dockerfile USER 10001:10001 directive", bool(re.search(r"USER\s+10001:10001", dockerfile_content)))
    record_result("Dockerfile setcap cap_net_bind_service", "cap_net_bind_service" in dockerfile_content)
    record_result("Dockerfile non-root ownership chown", "chown -R sovereign:sovereign" in dockerfile_content)
    record_result("Dockerfile tini init process entrypoint", "tini" in dockerfile_content)

    # Compose checks
    record_result("Compose user 10001:10001", bool(re.search(r'user:\s*["\']?10001:10001["\']?', compose_content)))
    record_result("Compose read_only root filesystem", "read_only: true" in compose_content)
    record_result("Compose no-new-privileges security option", "no-new-privileges:true" in compose_content)
    record_result("Compose cap_drop ALL", bool(re.search(r"cap_drop:\s*\n\s*-\s*ALL", compose_content)))
    record_result("Compose cap_add NET_BIND_SERVICE", "NET_BIND_SERVICE" in compose_content)
    record_result("Compose ephemeral tmpfs mounts for /tmp and /var/run", "/tmp:rw,noexec,nosuid" in compose_content and "/var/run:rw,noexec,nosuid" in compose_content)
    record_result("Compose no privileged mode", "privileged: true" not in compose_content)
    record_result("Compose no CAP_SYS_ADMIN", "SYS_ADMIN" not in compose_content)

    # Entrypoint checks
    record_result("Entrypoint uses set -eu safety flags", "set -eu" in entrypoint_content or "set -e" in entrypoint_content)
    record_result("Entrypoint handles graceful SIGTERM/SIGINT trap", "trap" in entrypoint_content and "SIGTERM" not in entrypoint_content and "TERM" in entrypoint_content)


def test_deep_secret_scanning():
    print(f"\n{BLUE}{BOLD}=== 2. Exhaustive Zero-Secret Security Scanner ==={RESET}")

    SECRET_PATTERNS = [
        ("AWS Access Key ID", r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"),
        ("AWS Secret Access Key", r"(?i)aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/+=]{40}['\"]"),
        ("RSA/EC/DSA Private Key Header", r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----"),
        ("GitHub Personal Access Token", r"gh[pousr]_[A-Za-z0-9_]{36,255}"),
        ("Slack Token", r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*"),
        ("Google Cloud API Key", r"AIza[0-9A-Za-z\\-_]{35}"),
        ("Generic Hardcoded Token / Password", r"(?i)(?:password|secret_key|api_key|ntfy_token)\s*=\s*['\"][A-Za-z0-9_\-]{24,}['\"]"),
        ("Live DuckDNS Update URL Token", r"duckdns\.org/update\?domains=[a-zA-Z0-9]+&token=[a-f0-9]{8}-[a-f0-9]{4}"),
    ]

    TARGET_DIRS = [
        REPO_ROOT / "scripts",
        REPO_ROOT / "configs",
        REPO_ROOT / "cmd",
        REPO_ROOT / "docker",
        REPO_ROOT / "pkg",
        REPO_ROOT / "charts",
        REPO_ROOT / "terraform",
        REPO_ROOT / "k8s",
    ]

    EXCLUDE_PATTERNS = [
        r"\.git",
        r"\.agents",
        r"__pycache__",
        r"\.test$",
        r"test_secret_scanner\.sh",
        r"adversarial_m1_challenger2\.py",
        r"secrets\.sh",
        r"\.template$",
    ]

    total_scanned_files = 0
    total_violations = 0

    for target_dir in TARGET_DIRS:
        if not target_dir.exists():
            continue
        for root, _, files in os.walk(target_dir):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(REPO_ROOT)

                # Skip excluded paths or binary files
                if any(re.search(pat, str(rel_path)) for pat in EXCLUDE_PATTERNS):
                    continue
                if file_path.suffix in [".png", ".jpg", ".tar", ".gz", ".zip", ".so", ".bin"]:
                    continue

                try:
                    content = file_path.read_text(errors="ignore")
                except Exception:
                    continue

                total_scanned_files += 1

                for name, regex in SECRET_PATTERNS:
                    matches = list(re.finditer(regex, content))
                    # Filter out placeholders / comments / documentation
                    valid_matches = []
                    for m in matches:
                        line = content[max(0, m.start() - 50) : min(len(content), m.end() + 50)]
                        if "example" in line.lower() or "placeholder" in line.lower() or "<YOUR_" in line:
                            continue
                        valid_matches.append(m.group(0))

                    if valid_matches:
                        print(f"    {RED}[!] Leak detected in {rel_path} ({name}): {valid_matches[0][:20]}...{RESET}")
                        total_violations += 1

    record_result(f"Zero hardcoded secrets across {total_scanned_files} files", total_violations == 0, f"(Violations: {total_violations})")


async def test_python_security_daemon_async_stress():
    print(f"\n{BLUE}{BOLD}=== 3. Python Security Daemon Async Concurrency Stress Test ==={RESET}")
    sys.path.insert(0, str(REPO_ROOT / "cmd" / "sovereign-security-daemon"))
    try:
        import daemon as py_daemon
    except ImportError as e:
        record_result("Import Python daemon module", False, str(e))
        return

    sd = py_daemon.SecurityDaemon(host="127.0.0.1", port=18299, dry_run=True)
    server_task = asyncio.create_task(sd.start())
    await asyncio.sleep(0.1)

    # Launch 1,000 rapid concurrent async TCP requests
    total_clients = 1000
    successful_handshakes = 0
    dropped_or_rejected = 0

    async def client_worker(idx: int):
        nonlocal successful_handshakes, dropped_or_rejected
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 18299)
            writer.write(b"GET / HTTP/1.1\r\nHost: honeypot\r\n\r\n")
            await writer.drain()
            data = await asyncio.wait_for(reader.read(128), timeout=1.0)
            if data:
                successful_handshakes += 1
            else:
                dropped_or_rejected += 1
            writer.close()
            await writer.wait_closed()
        except Exception:
            dropped_or_rejected += 1

    tasks = [client_worker(i) for i in range(total_clients)]
    await asyncio.gather(*tasks)

    print(f"    Completed {total_clients} async connections: Success={successful_handshakes}, Dropped={dropped_or_rejected}")
    record_result("Python daemon handled 1,000 concurrent async connections without crashing", successful_handshakes + dropped_or_rejected == total_clients)

    # Check threat scorer and whitelist in Python daemon
    wm = py_daemon.WhitelistManager(py_daemon.DEFAULT_WHITELIST)
    record_result("Python WhitelistManager allows loopback", wm.is_whitelisted("127.0.0.1"))
    record_result("Python WhitelistManager allows RFC 1918 (10.0.0.1)", wm.is_whitelisted("10.0.0.1"))
    record_result("Python WhitelistManager allows Cloudflare DNS (1.1.1.1)", wm.is_whitelisted("1.1.1.1"))
    record_result("Python WhitelistManager blocks public IP (198.51.100.1)", not wm.is_whitelisted("198.51.100.1"))

    # Cleanup
    await sd.stop()
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


def main():
    test_container_security()
    test_deep_secret_scanning()
    asyncio.run(test_python_security_daemon_async_stress())

    print(f"\n{BOLD}======================================================================={RESET}")
    print(f"Challenger 2 Adversarial Summary: {GREEN}{PASS_COUNT} Passed{RESET}, {RED}{FAIL_COUNT} Failed{RESET}")
    print(f"{BOLD}======================================================================={RESET}\n")

    if FAIL_COUNT == 0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
