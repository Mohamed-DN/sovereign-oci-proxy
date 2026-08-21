# ❓ Frequently Asked Questions

**Q: Will I be charged by Oracle?**
A: No. As long as you stay within the 4 OCPUs, 24GB RAM, and 10TB outbound bandwidth limits, the Always Free tier incurs zero charges.

**Q: Why does my IP show up as Cloudflare when I test my VPN?**
A: This is an intentional security feature. We route the Xray traffic through Cloudflare WARP (WireGuard) using the Outbound routing rules. This hides the Oracle Datacenter IP, reducing the chance of being blocked by streaming services or banking apps.

**Q: Can I use this to access my home Proxmox server?**
A: Yes! By installing Tailscale on this Oracle instance and configuring it as a mesh node, Xray routes internal traffic directly to your Homelab securely.
