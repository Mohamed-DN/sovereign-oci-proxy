#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 - Hardened Decoy Web Engine Deployment
# Location: scripts/legacy_refactor/decoy.sh
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

DECOY_ROOT="${SOVEREIGN_DECOY_ROOT:-/var/www/decoy}"
NGINX_CONF_SRC="${PROJECT_ROOT}/configs/nginx/decoy.conf"
NGINX_CONF_DST="${SOVEREIGN_NGINX_CONF_DST:-/etc/nginx/conf.d/decoy.conf}"

log_info() { echo -e "\033[0;34m[+] INFO:\033[0m $1"; }
log_ok() { echo -e "\033[0;32m[✓] SUCCESS:\033[0m $1"; }
log_err() { echo -e "\033[0;31m[✗] ERROR:\033[0m $1" >&2; }

deploy_decoy_site() {
    log_info "Deploying authentic Cloud Infrastructure decoy dashboard to ${DECOY_ROOT}..."

    mkdir -p "${DECOY_ROOT}"

    cat << 'EOF' > "${DECOY_ROOT}/index.html"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Global Edge Operations | Telemetry & Infrastructure Health</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-color: #38bdf8;
            --status-green: #22c55e;
            --border-color: #334155;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            margin: 0;
            padding: 2rem;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        header {
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 { margin: 0; font-size: 1.5rem; font-weight: 600; }
        .status-pill {
            background-color: rgba(34, 197, 94, 0.15);
            color: var(--status-green);
            padding: 0.35rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            background-color: var(--status-green);
            border-radius: 50%;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            padding: 1.5rem;
        }
        .card-title {
            color: var(--text-secondary);
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }
        .card-value {
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--accent-color);
        }
        footer {
            margin-top: 3rem;
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-align: center;
            border-top: 1px solid var(--border-color);
            padding-top: 1.5rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Edge Gateway Telemetry Service</h1>
                <p style="color: var(--text-secondary); margin: 0.25rem 0 0 0; font-size: 0.9rem;">Cluster Node: edge-prod-04.internal</p>
            </div>
            <div class="status-pill">
                <span class="status-dot"></span> All Systems Operational
            </div>
        </header>

        <div class="grid">
            <div class="card">
                <div class="card-title">Network Ingress Throughput</div>
                <div class="card-value">1.48 Gbps</div>
            </div>
            <div class="card">
                <div class="card-title">Mean Edge Latency</div>
                <div class="card-value">14.2 ms</div>
            </div>
            <div class="card">
                <div class="card-title">TLS 1.3 Session Cache</div>
                <div class="card-value">99.8%</div>
            </div>
            <div class="card">
                <div class="card-title">Active BGP Peering</div>
                <div class="card-value">6 / 6 Sessions</div>
            </div>
            <div class="card">
                <div class="card-title">Packet Drop Ratio</div>
                <div class="card-value">&lt; 0.001%</div>
            </div>
            <div class="card">
                <div class="card-title">Security State</div>
                <div class="card-value" style="color: var(--status-green)">Hardened</div>
            </div>
        </div>

        <footer>
            &copy; 2026 Global Edge Infrastructure Network. Internal Operational Telemetry.
        </footer>
    </div>
</body>
</html>
EOF

    cat << 'EOF' > "${DECOY_ROOT}/404.html"
<!DOCTYPE html>
<html><head><title>404 Not Found</title></head>
<body style="background:#0f172a;color:#94a3b8;font-family:sans-serif;text-align:center;padding:5rem;">
<h1>404 Not Found</h1>
<p>The requested resource is not available on this edge cluster node.</p>
<hr style="border-color:#334155;max-width:400px;margin:2rem auto;">
<small>nginx/1.26.1</small>
</body></html>
EOF

    cat << 'EOF' > "${DECOY_ROOT}/50x.html"
<!DOCTYPE html>
<html><head><title>500 Internal Server Error</title></head>
<body style="background:#0f172a;color:#94a3b8;font-family:sans-serif;text-align:center;padding:5rem;">
<h1>500 Internal Server Error</h1>
<p>Edge upstream service temporarily unavailable.</p>
<hr style="border-color:#334155;max-width:400px;margin:2rem auto;">
<small>nginx/1.26.1</small>
</body></html>
EOF

    log_ok "Decoy web pages deployed to ${DECOY_ROOT}."
}

deploy_nginx_config() {
    log_info "Deploying Nginx decoy configuration from ${NGINX_CONF_SRC}..."

    if [[ -d "/etc/nginx/conf.d" ]] && [[ "$(id -u)" -eq 0 ]]; then
        cp "$NGINX_CONF_SRC" "$NGINX_CONF_DST"
        if command -v nginx >/dev/null 2>&1; then
            if nginx -t; then
                systemctl reload nginx || systemctl restart nginx || true
                log_ok "Nginx decoy configuration validated and applied."
            else
                log_err "Nginx syntax test failed!"
                return 1
            fi
        fi
    else
        log_ok "Nginx decoy configuration verified in ${NGINX_CONF_SRC}"
    fi
}

main() {
    deploy_decoy_site
    deploy_nginx_config
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
