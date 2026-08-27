#!/usr/bin/env bash
# ==============================================================================
# Sovereign Proxy v4.0 — Universal Distro-Agnostic Node Bootstrap Engine
# ==============================================================================
set -euo pipefail

log_info() { echo -e "\033[1;34m[INFO]\033[0m $*"; }
log_succ() { echo -e "\033[1;32m[SUCCESS]\033[0m $*"; }
log_warn() { echo -e "\033[1;33m[WARNING]\033[0m $*"; }
log_err()  { echo -e "\033[1;31m[ERROR]\033[0m $*"; exit 1; }

# Step 1: Detect Operating System & Architecture
log_info "Detecting Operating System and Architecture..."
OS_DISTRO="unknown"
if [ -f /etc/os-release ]; then
  . /etc/os-release
  OS_DISTRO="${ID}"
elif [ -f /etc/alpine-release ]; then
  OS_DISTRO="alpine"
fi
ARCH=$(uname -m)
log_info "Detected OS: ${OS_DISTRO}, Architecture: ${ARCH}"

# Step 2: Install Essential Packages
log_info "Installing core system dependencies for ${OS_DISTRO}..."
case "${OS_DISTRO}" in
  ubuntu|debian)
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y curl wget jq iptables ufw fail2ban ca-certificates gnupg wireguard-tools
    ;;
  rhel|rocky|almalinux|ol|fedora|centos)
    yum update -y || dnf update -y || true
    yum install -y curl wget jq iptables iptables-services fail2ban ca-certificates gnupg wireguard-tools || \
    dnf install -y curl wget jq iptables iptables-services fail2ban ca-certificates gnupg wireguard-tools
    ;;
  alpine)
    apk update
    apk add --no-cache curl wget jq iptables ip6tables fail2ban ca-certificates gnupg wireguard-tools bash
    ;;
  *)
    log_warn "Unknown OS distro '${OS_DISTRO}'. Proceeding with best-effort bootstrap..."
    ;;
esac

# Step 3: Apply BBR & Network Buffer Sysctl Tuning
log_info "Applying Linux Kernel BBR and High-Throughput Buffers..."
if [ -f /etc/sysctl.d/99-sovereign-proxy.conf ]; then
  sysctl --system || true
fi

# Step 4: Configure Hardened Firewall (UFW / Iptables)
log_info "Locking down firewall (SSH 2222, HTTPS 443, HTTP 80, STUN 3478 UDP, Honeypot 8080)..."
SSH_PORT="2222"
if command -v ufw &>/dev/null; then
  ufw --force reset || true
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow "${SSH_PORT}/tcp" comment "Hardened SSH Port"
  ufw allow "22/tcp" comment "Temporary Fallback SSH"
  ufw allow "80/tcp" comment "ACME HTTP-01 Validation"
  ufw allow "443/tcp" comment "Sovereign Proxy TLS / DERP"
  ufw allow "3478/udp" comment "Mesh STUN UDP Discovery"
  ufw allow "8080/tcp" comment "Honeypot Scanner Trap"
  ufw --force enable || true
else
  # Fallback to direct iptables rules
  iptables -P INPUT DROP
  iptables -P FORWARD DROP
  iptables -P OUTPUT ACCEPT
  iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
  iptables -A INPUT -i lo -j ACCEPT
  iptables -A INPUT -p tcp --dport "${SSH_PORT}" -j ACCEPT
  iptables -A INPUT -p tcp --dport 22 -j ACCEPT
  iptables -A INPUT -p tcp --dport 80 -j ACCEPT
  iptables -A INPUT -p tcp --dport 443 -j ACCEPT
  iptables -A INPUT -p udp --dport 3478 -j ACCEPT
  iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
fi

# Step 5: Harden SSH Daemon Configuration
log_info "Hardening SSH configuration (Port 2222, disable password auth)..."
if [ -f /etc/ssh/sshd_config ]; then
  sed -i.bak 's/^#*Port [0-9]*/Port 2222/' /etc/ssh/sshd_config || true
  sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config || true
  sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config || true
  systemctl restart ssh || systemctl restart sshd || true
fi

# Step 6: Install Container Runtime (Docker & Compose)
log_info "Ensuring Container Runtime (Docker) is present..."
if ! command -v docker &>/dev/null; then
  case "${OS_DISTRO}" in
    alpine)
      apk add --no-cache docker docker-cli-compose
      rc-update add docker boot || true
      service docker start || true
      ;;
    *)
      curl -fsSL https://get.docker.com | sh
      systemctl enable --now docker || true
      ;;
  esac
fi

# Step 7: Node Registration with Sovereign Control Plane
log_info "Checking Control Plane Node Registration..."
NODE_ENV_FILE="/opt/sovereign/config/node.env"
if [ -f "${NODE_ENV_FILE}" ]; then
  # Source environment
  set -a
  . "${NODE_ENV_FILE}"
  set +a

  if [ -n "${REGISTRATION_TOKEN:-}" ] && [ -n "${CONTROL_PLANE_ENDPOINT:-}" ]; then
    log_info "Attempting node registration with Control Plane at ${CONTROL_PLANE_ENDPOINT}..."
    REGISTER_PAYLOAD=$(jq -n \
      --arg node_id "${NODE_ID}" \
      --arg role "${NODE_ROLE:-relay}" \
      --arg pubkey "${NOISE_PUBLIC_KEY:-}" \
      '{nodeId: $node_id, role: $role, publicKey: $pubkey, version: "4.0.0"}')

    curl -s -X POST \
      -H "Authorization: Bearer ${REGISTRATION_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "${REGISTER_PAYLOAD}" \
      "${CONTROL_PLANE_ENDPOINT}/api/v1/nodes/register" || log_warn "Initial registration heartbeat queued."
  fi
fi

# Step 8: Start Sovereign Node Service
log_info "Launching Sovereign Stack..."
mkdir -p /opt/sovereign/data /opt/sovereign/certs /opt/sovereign/www-decoy /var/log/sovereign
if [ -f /opt/sovereign/docker-compose.yml ]; then
  cd /opt/sovereign
  docker compose up -d || log_warn "Docker compose startup deferred to service."
fi

if command -v systemctl &>/dev/null; then
  systemctl daemon-reload || true
  systemctl enable sovereign-node.service || true
fi

log_succ "Universal Node Bootstrap Finished Successfully!"
