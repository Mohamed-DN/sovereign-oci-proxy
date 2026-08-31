# Sovereign Proxy v4.0 - Hardened Container Architecture

## Overview
Sovereign Proxy v4.0 container images are designed from the ground up to adhere to strict zero-trust, rootless container security principles.

### Key Security Features:
1. **Unprivileged User Execution**: Operates strictly under dedicated UID `10001` and GID `10001`.
2. **Read-Only Root Filesystem**: The container root filesystem is mounted read-only (`read_only: true`), preventing unauthorized file modification or malicious payload persistence.
3. **Dropped Linux Capabilities**: Drops all default capabilities (`cap_drop: [ALL]`) and retains only `NET_BIND_SERVICE` for low-port binding.
4. **`no-new-privileges` Enforced**: Blocks privilege escalation via setuid/setgid binaries.
5. **In-Memory Tmpfs Mounts**: Uses isolated memory-backed mounts for logs, temporary buffers, and PID files.
6. **Multi-Stage Minimal Base**: Multi-stage build packaging only runtime dependencies on top of Alpine Linux.

## Running with Docker Compose

```bash
# 1. Generate secrets or provide in environment
export CLIENT_UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
export REALITY_PRIVATE_KEY="<YOUR_PRIVATE_KEY>"
export REALITY_SHORT_ID="<YOUR_SHORT_ID>"

# 2. Build and launch
docker compose -f docker/docker-compose.yml up -d

# 3. Check logs and health status
docker compose -f docker/docker-compose.yml ps
docker compose -f docker/docker-compose.yml logs -f
```
