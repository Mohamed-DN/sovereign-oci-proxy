# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [1.0.0] - 2024-08-21

### Added
- Initial release of the Sovereign OCI Proxy
- VLESS + REALITY + XTLS-Vision proxy on Oracle Cloud Free Tier (ARM A1.Flex)
- Nginx decoy site for active probing defense
- Python honeypot with auto-ban on port 8080
- Oracle anti-idle keepalive script (prevents instance reclamation)
- DuckDNS auto-updater with retry logic and failure alerts
- GPG asymmetric backup pipeline to Backblaze B2
- Xray routing fix for Tailscale/Homelab private IP access
- 3x-ui client injection fix for v3.6.0+ relational database schema
- Cloudflare WARP integration for datacenter IP masking
- UFW + Fail2ban + Auditd multi-layer hardening
- BBR congestion control and TCP tuning
- Systemd service for honeypot with auto-restart
- 20-point automated validation test suite
- Full documentation: Architecture, Quickstart, Full Guide, Troubleshooting, FAQ
- GitHub Actions CI pipeline with ShellCheck and secret scanning
- Docker support (experimental)
