# 🐳 Docker Support (Experimental)

> **⚠️ WARNING:** Docker support is currently in **BETA**. The recommended deployment method is bare-metal installation using the scripts in `scripts/modules/`. Docker is provided for testing and development purposes.

## Quick Start

```bash
# Build the image
cd sovereign-oci-proxy
docker compose -f docker/docker-compose.yml build

# Start the container
docker compose -f docker/docker-compose.yml up -d

# View logs
docker compose -f docker/docker-compose.yml logs -f
```

## Post-Start Configuration

After the container is running, you must install 3x-ui manually:

```bash
# Enter the container
docker exec -it sovereign-proxy bash

# Install 3x-ui
bash <(curl -Ls https://raw.githubusercontent.com/MHSanaei/3x-ui/master/install.sh)
```

## Volumes

| Volume | Purpose |
| --- | --- |
| `proxy-data` | 3x-ui database and configuration |
| `proxy-certs` | SSL/TLS certificates |
| `proxy-logs` | Application and access logs |

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `TZ` | `Europe/Rome` | Server timezone |

## Limitations

- Tailscale mesh networking requires `--network=host` mode (not included by default)
- UFW firewall rules must be managed on the host, not inside the container
- The honeypot requires `CAP_NET_ADMIN` capability (included in compose file)

## Stopping

```bash
docker compose -f docker/docker-compose.yml down
```

To also remove volumes (deletes all data):
```bash
docker compose -f docker/docker-compose.yml down -v
```
