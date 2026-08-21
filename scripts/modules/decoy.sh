#!/bin/bash
# Nginx Decoy Setup

apt-get update && apt-get install -y nginx
mkdir -p /var/www/decoy

cat << 'HTML_EOF' > /var/www/decoy/index.html
<!DOCTYPE html>
<html>
<head><title>Cloud Infrastructure Monitor</title></head>
<body style="background:#0a0a0a;color:#4ade80;text-align:center;padding:50px;font-family:sans-serif;">
    <h1>All systems operational</h1>
    <p>Uptime: 99.98%</p>
</body>
</html>
HTML_EOF

cat << 'NGINX_EOF' > /etc/nginx/sites-available/decoy
server {
    listen 127.0.0.1:8443;
    server_name _;
    root /var/www/decoy;
    index index.html;
}
NGINX_EOF

ln -sf /etc/nginx/sites-available/decoy /etc/nginx/sites-enabled/decoy
systemctl restart nginx
