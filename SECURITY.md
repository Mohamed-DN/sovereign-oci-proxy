# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via [GitHub Security Advisories](https://github.com/Mohamed-DN/sovereign-oci-proxy/security/advisories/new).

You should receive a response within 48 hours. If the issue is confirmed, we will release a patch as soon as possible depending on the complexity of the fix.

## Response Timeline

| Action                     | Timeframe       |
| -------------------------- | --------------- |
| Acknowledgment of report   | Within 48 hours |
| Initial assessment         | Within 72 hours |
| Patch release (if needed)  | Within 7 days   |

## Disclosure Policy

- We follow a **coordinated disclosure** model
- Reporters will be credited in the changelog (unless they prefer anonymity)
- Vulnerabilities will be disclosed publicly only after a fix is available

## Security Design Principles

This project is built on the following security principles:

### Zero Secrets on Server
The Oracle VPS holds **no private keys** for backup decryption. Even if the server is fully compromised, the attacker cannot decrypt backup archives stored on Backblaze B2.

### Asymmetric Encryption
All backups are encrypted using GPG with the user's **public key only**. Decryption requires the private key, which must be stored offline (e.g., in a password manager like Vaultwarden, never on the server).

### Defense in Depth
Multiple independent security layers protect the infrastructure:
1. **Network Layer**: UFW firewall with default-deny incoming policy
2. **Application Layer**: Fail2ban monitors SSH and Nginx for brute-force attempts
3. **Deception Layer**: Honeypot on port 8080 catches and bans scanners
4. **Protocol Layer**: VLESS+REALITY makes the proxy indistinguishable from legitimate HTTPS traffic
5. **Audit Layer**: Auditd logs all privileged operations and config changes
6. **Monitoring Layer**: Health checks every 5 minutes with push notifications on failure

### Principle of Least Privilege
- SSH root login is disabled
- SSH password authentication is disabled
- The 3x-ui admin panel is accessible only via the Tailscale interface (never exposed publicly)
- IPv6 is disabled to reduce attack surface

## Known Limitations

- The DuckDNS token and Ntfy topic URL are stored in plaintext scripts on the server. These are low-sensitivity credentials (DuckDNS only updates DNS, Ntfy is a notification channel), but users should be aware.
- The 3x-ui SQLite database (`x-ui.db`) contains user UUIDs. It is protected by filesystem permissions (`chmod 600`) and encrypted before offsite backup.
