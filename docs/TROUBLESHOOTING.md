# 🔧 Troubleshooting

### 1. I locked myself out of SSH!
Did you change the port to 2222 but forgot to open it in the Oracle Cloud Console Security List? 
**Fix:** Go to the Oracle Cloud Web Console, navigate to your VCN's Security List, and add an Ingress rule for TCP port 2222.

### 2. Tailscale Homelab IPs are unreachable
By default, Xray blocks all private IPs (`geoip:private`) to prevent SSRF attacks. 
**Fix:** Run the `scripts/modules/xray-routing-fix.py` script provided in this repository. It edits the SQLite database to allow `geoip:private` traffic to flow to the `direct` outbound, making Tailscale work.

### 3. Clients are silently dropping in 3x-ui v3.6.0
**Fix:** In newer versions, adding clients to the JSON payload is ignored. Use `scripts/modules/xray-client-fix.py` to correctly inject users into the relational SQLite tables.
