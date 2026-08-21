FROM ubuntu:24.04

LABEL maintainer="Mohamed-DN"
LABEL description="Sovereign OCI Proxy - Anti-Censorship VLESS+REALITY Proxy"

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install base packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    nginx \
    python3 \
    jq \
    sqlite3 \
    gnupg2 \
    bc \
    net-tools \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Create required directories
RUN mkdir -p /var/www/decoy /var/log/xray /opt/duckdns /root/backups

# Copy configuration files
COPY configs/nginx/decoy.conf /etc/nginx/sites-available/decoy
COPY configs/sysctl/sovereign.conf /etc/sysctl.d/99-sovereign.conf

# Copy scripts
COPY scripts/ /opt/sovereign/scripts/

# Copy decoy site (generated during install)
COPY configs/nginx/decoy.conf /etc/nginx/sites-available/decoy
RUN ln -sf /etc/nginx/sites-available/decoy /etc/nginx/sites-enabled/decoy && \
    rm -f /etc/nginx/sites-enabled/default

# Expose ports
EXPOSE 443 80 8080

# Health check
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD curl -sf http://127.0.0.1:8443/api/status || exit 1

# Note: 3x-ui must be installed manually inside the container.
# See docker/README.md for instructions.
CMD ["nginx", "-g", "daemon off;"]
