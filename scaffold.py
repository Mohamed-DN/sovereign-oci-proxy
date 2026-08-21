import os

base_dir = r"C:\home_server\sovereign-oci-proxy"

directories = [
    "docs",
    "scripts/modules",
    "configs/nginx",
    "configs/xray",
    "configs/sysctl",
    "configs/systemd",
    "docker",
    "tests",
    "assets",
    ".github/ISSUE_TEMPLATE",
    ".github/workflows"
]

files = {
    "LICENSE": "AGPL-3.0 License\n",
    "CONTRIBUTING.md": "# Guida per contributori\n",
    "CODE_OF_CONDUCT.md": "# Regole community\n",
    "CHANGELOG.md": "# Storia versioni\n\n## [1.0.0] - 2026-08-21\n- Initial release basata su S.O.A.P. 6.2\n",
    "SECURITY.md": "# Security Policy\n",
    "docs/ARCHITECTURE.md": "# Diagramma Architettura\n",
    "docs/QUICKSTART.md": "# Setup in 5 minuti\n",
    "docs/FULL_GUIDE.md": "# Guida Completa (S.O.A.P. 6.2)\n",
    "docs/TROUBLESHOOTING.md": "# Risoluzione problemi\n",
    "docs/FAQ.md": "# Domande frequenti\n",
    "scripts/install.sh": "#!/bin/bash\necho 'Sovereign OCI Proxy Installer'\n",
    "scripts/uninstall.sh": "#!/bin/bash\necho 'Uninstalling...'\n",
    "scripts/sovereign-setup": "#!/bin/bash\n# TUI Configurator\n",
    "scripts/modules/hardening.sh": "#!/bin/bash\n# Sysctl, Swap, SSH, Fail2ban, UFW\n",
    "scripts/modules/duckdns.sh": "#!/bin/bash\n# DuckDNS Auto-updater\n",
    "scripts/modules/decoy.sh": "#!/bin/bash\n# Nginx Decoy Setup\n",
    "scripts/modules/xray.sh": "#!/bin/bash\n# 3x-ui and Routing Setup\n",
    "scripts/modules/backup.sh": "#!/bin/bash\n# GPG Asymmetric Encryption + Backblaze B2\n",
    "scripts/modules/monitoring.sh": "#!/bin/bash\n# Healthchecks, Honeypot, Keepalive\n",
    "configs/nginx/decoy.conf": "server { listen 127.0.0.1:8443; }\n",
    "configs/xray/config.json.template": "{\n  \"inbounds\": [],\n  \"outbounds\": []\n}\n",
    "configs/sysctl/sovereign.conf": "net.ipv4.tcp_congestion_control = bbr\n",
    "configs/systemd/honeypot.service": "[Unit]\nDescription=Sovereign Honeypot\n",
    "configs/systemd/health-check.service": "[Unit]\nDescription=Health Check\n",
    "docker/Dockerfile": "FROM ubuntu:24.04\n",
    "docker/docker-compose.yml": "services:\n  sovereign:\n    image: sovereign-proxy\n",
    "docker/README.md": "# Docker Setup\n",
    "tests/test-install.sh": "#!/bin/bash\n",
    "tests/test-health-check.sh": "#!/bin/bash\n",
    "tests/test-backup.sh": "#!/bin/bash\n",
    ".github/FUNDING.yml": "github: Mohamed-DN\n",
    ".github/ISSUE_TEMPLATE/bug_report.md": "---\nname: Bug report\n---\n",
    ".github/ISSUE_TEMPLATE/feature_request.md": "---\nname: Feature request\n---\n",
    ".github/workflows/ci.yml": "name: CI\n",
    ".github/workflows/release.yml": "name: Release\n",
}

for d in directories:
    os.makedirs(os.path.join(base_dir, d), exist_ok=True)

for fpath, content in files.items():
    full_path = os.path.join(base_dir, fpath)
    if not os.path.exists(full_path):
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

print("Scaffold completato con successo.")
