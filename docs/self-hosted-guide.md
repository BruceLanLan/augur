# Self-Hosted Deployment Guide (H04)

Augur is designed for local-first operation. This guide covers deploying
Augur in self-hosted environments for individual or small-team use.

## Quick Deploy

```bash
git clone https://github.com/BruceLanLan/augur.git
cd augur
pip install -e ".[data]"

# Set data directory (recommended)
export AUGUR_DATA_DIR=/var/lib/augur

# Local only (default since v11.0.0-rc1: binds 127.0.0.1)
augur serve --port 8000

# Reachable from other machines: turn authentication on first
export AUGUR_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
augur serve --host 0.0.0.0 --port 8000
```

> Without `AUGUR_API_TOKEN` (or `AUGUR_MULTI_USER=1`) every `/api/*` endpoint,
> including config and data changes, is open to anyone who can reach the port.
> `augur serve` prints a warning when you bind beyond loopback without auth.
> `augur api` (the separate REST server) has no authentication at all; keep it
> on 127.0.0.1 or behind an authenticating reverse proxy.

## Docker Deploy

```bash
docker compose up -d
# Dashboard: http://localhost:8000
# MCP: stdio mode, connect via Claude Desktop config
```

## Systemd Service

```ini
# /etc/systemd/system/augur.service
[Unit]
Description=Augur Dashboard
After=network.target

[Service]
Type=simple
User=augur
WorkingDirectory=/opt/augur
Environment=AUGUR_DATA_DIR=/var/lib/augur
# Required when binding 0.0.0.0; generate one and keep it out of version control
EnvironmentFile=/etc/augur/augur.env
ExecStart=/opt/augur/.venv/bin/augur serve --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now augur
```

## Reverse Proxy (nginx)

```nginx
server {
    listen 443 ssl;
    server_name augur.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Security Checklist

- [ ] Set `AUGUR_CORS_ORIGINS` to your domain (not `*`)
- [ ] Use HTTPS with valid certificates
- [ ] Set `AUGUR_JWT_SECRET` (or let Augur generate one)
- [ ] Enable firewall: only expose port 8000 to localhost + reverse proxy
- [ ] Regular backups: `cp -r $AUGUR_DATA_DIR /backup/augur-$(date +%Y%m%d)`
- [ ] Monitor: `augur doctor --offline` daily cron

## Data Backup

```bash
#!/bin/bash
# /etc/cron.daily/augur-backup
tar -czf /backup/augur-$(date +%Y%m%d).tar.gz $AUGUR_DATA_DIR
find /backup/ -name 'augur-*.tar.gz' -mtime +30 -delete
```

## Upgrading

```bash
cd /opt/augur
git pull origin main
pip install -e ".[data]"
systemctl restart augur
augur doctor --offline
```

## Resource Requirements

| Component | Minimum | Recommended |
|---|---|---|
| RAM | 512 MB | 2 GB |
| Disk | 1 GB | 10 GB (for EDGAR cache) |
| Python | 3.9+ | 3.11+ |

## Troubleshooting

- **Import errors**: `pip install -e ".[data]"` to ensure all deps
- **Dashboard fails to start**: check `AUGUR_DATA_DIR` is writable
- **MCP not connecting**: verify `augur-mcp` entry point exists
- **Slow startup**: first run downloads EDGAR data; subsequent runs use cache
