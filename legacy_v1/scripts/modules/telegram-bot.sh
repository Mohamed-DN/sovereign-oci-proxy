#!/bin/bash
# =========================================================
# Sovereign Proxy - Telegram C2 Bot
# Deploys a lightweight Python bot to manage the server
# directly from Telegram (QR codes, status, alerts).
# =========================================================

set -e
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[!] Please run as root${NC}"
    exit 1
fi

source /opt/sovereign-oci-proxy/config.env 2>/dev/null || true

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_ADMIN_ID" ]; then
    echo -e "${RED}[!] TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_ID not found in config.env!${NC}"
    exit 1
fi

echo -e "${GREEN}[*] Installing dependencies...${NC}"
apt update -qq
apt install -y python3-requests qrencode

echo -e "${GREEN}[*] Deploying Bot Script...${NC}"
cat << 'BOT_EOF' > /usr/local/bin/sovereign-telebot.py
#!/usr/bin/env python3
import os
import time
import requests
import subprocess

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("TELEGRAM_ADMIN_ID"))
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def get_updates(offset=None):
    url = f"{API_URL}/getUpdates?timeout=60"
    if offset:
        url += f"&offset={offset}"
    try:
        resp = requests.get(url, timeout=65)
        return resp.json()
    except Exception:
        return None

def send_message(text):
    requests.post(f"{API_URL}/sendMessage", json={"chat_id": ADMIN_ID, "text": text, "parse_mode": "Markdown"})

def send_photo(photo_path, caption=""):
    with open(photo_path, 'rb') as p:
        requests.post(f"{API_URL}/sendPhoto", data={"chat_id": ADMIN_ID, "caption": caption}, files={"photo": p})

def handle_message(text):
    if text == "/status":
        uptime = subprocess.getoutput("uptime -p")
        mem = subprocess.getoutput("free -m | awk 'NR==2{printf \"%.2f%%\", $3*100/$2 }'")
        send_message(f"🛡️ *Sovereign OCI Proxy*\n\n⏱️ {uptime}\n🧠 RAM: {mem}\n✅ All systems nominal.")
    
    elif text == "/clients":
        out = subprocess.getoutput("wg show wg0")
        send_message(f"📡 *WireGuard Clients*\n```\n{out}\n```")
    
    elif text.startswith("/qr"):
        parts = text.split()
        if len(parts) < 2:
            send_message("Usage: `/qr <client_name>`")
            return
        client = parts[1]
        conf_path = f"/etc/wireguard/clients/{client}/{client}.conf"
        if os.path.exists(conf_path):
            img_path = f"/tmp/{client}_qr.png"
            subprocess.run(["qrencode", "-t", "PNG", "-o", img_path, "-r", conf_path])
            send_photo(img_path, f"QR Code for {client}")
            os.remove(img_path)
        else:
            send_message(f"❌ Client '{client}' not found.")
            
    else:
        send_message("🤖 *Available Commands:*\n/status - System health\n/clients - Active WG peers\n/qr <name> - Get client QR code")

def main():
    print("Sovereign Telegram C2 Bot Started.")
    send_message("🤖 *Sovereign Proxy Bot Online*\nReady for commands.")
    offset = None
    while True:
        updates = get_updates(offset)
        if updates and "result" in updates:
            for update in updates["result"]:
                offset = update["update_id"] + 1
                if "message" in update and "text" in update["message"]:
                    chat_id = update["message"]["chat"]["id"]
                    if chat_id != ADMIN_ID:
                        continue # Ignore unauthorized users
                    handle_message(update["message"]["text"])
        time.sleep(1)

if __name__ == "__main__":
    main()
BOT_EOF

chmod +x /usr/local/bin/sovereign-telebot.py

echo -e "${GREEN}[*] Creating Systemd Service...${NC}"
cat << SVC_EOF > /etc/systemd/system/sovereign-telebot.service
[Unit]
Description=Sovereign Telegram C2 Bot
After=network.target

[Service]
ExecStart=/usr/local/bin/sovereign-telebot.py
Environment="TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}"
Environment="TELEGRAM_ADMIN_ID=${TELEGRAM_ADMIN_ID}"
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
SVC_EOF

systemctl daemon-reload
systemctl enable --now sovereign-telebot

echo -e "${GREEN}[*] Telegram Bot Deployed and Running!${NC}"
echo -e "${GREEN}    Open Telegram and send /status to your bot.${NC}"
