# 📖 Full Operations Manual (S.O.A.P. 6.2)

## 1. Initial Hardening
The `hardening.sh` module configures:
- 4GB Swap file for memory safety.
- BBR Congestion Control for network speed optimization.
- SSH Port changed to 2222 (Root login disabled, password auth disabled).
- Fail2ban jails for SSH and Nginx bot searches.
- UFW Firewall locking down everything except 2222, 443, 80, and 8080.

## 2. Decoy Setup
The `decoy.sh` module configures Nginx on `127.0.0.1:8443`.
Any unauthorized connection to the Xray server on port 443 (e.g., active probing from Great Firewall or ISP) is seamlessly handed over to Nginx. Nginx returns a perfectly valid, harmless HTML page mimicking a "Cloud Infrastructure Monitor".

## 3. VLESS + REALITY
Use the 3x-ui panel to configure your inbound.
- **Protocol:** VLESS
- **Security:** REALITY
- **Flow:** xtls-rprx-vision
- **Dest/SNI:** Use a highly reputable SNI (e.g., `aws.amazon.com` or `www.cisco.com`).

## 4. Anti-Idle & Monitoring
Oracle terminates free instances if CPU/Network usage is <10% for 7 days.
The `monitoring.sh` module deploys a Keepalive script running every 4 hours that artificially spikes CPU (calculating Pi), Memory (allocating 500MB), and Network (pinging Google) to prevent reclamation.

## 5. Disaster Recovery
The `backup.sh` module utilizes GPG asymmetric encryption. It archives the SQLite database, encrypts it with your public key, and uploads it to Backblaze B2. You must hold the private key on your local machine to restore the database in the event of an instance termination.
