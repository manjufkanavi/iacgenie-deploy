# IacGenie Infrastructure — Ansible Deployment Guide

## Overview

This repository contains Ansible playbooks, roles, and templates for deploying the IacGenie platform stack on Ubuntu 24.04 VMs.

**Target VM:** `192.168.0.118`  
**SSH User:** `mkanavi`  
**Docker Network:** `iacgenie-network` (172.28.0.0/16)  
**Docker Version:** 29.x

## Quick Start

### Prerequisites

- Ubuntu 24.04 (not elementary OS — use `jammy` codename for Docker apt repos)
- 15GB+ RAM available
- SSH access with key-based auth
- Docker Compose v2 plugin installed

### Bootstrap

```bash
ansible-playbook playbooks/bootstrap.yml -i inventory/hosts
```

This installs Docker, configures system hardening (UFW, fail2ban, NTP), creates deployment user, and sets up the Ansible environment.

### Deploy Services

```bash
ansible-playbook playbooks/services.yml -i inventory/hosts
```

Generates Docker Compose files via Jinja2 templates and starts all 11 microservices.

### Validate

```bash
ansible-playbook playbooks/validate-services.yml -i inventory/hosts
```

Runs health checks against all running containers.

## Service Matrix

> **Last verified:** 2026-08-02

| # | Service | Image | Port | Resources | Health Check |
|---|---------|-------|------|-----------|-------------|
| 1 | PostgreSQL 15 | `postgres:15-alpine` | `127.0.0.1:5432` | 1536 MB / 0.75 CPU | `pg_isready -U postgres` |
| 2 | Redis 7 | `redis:7-alpine` | `127.0.0.1:6379` | 256 MB / 0.25 CPU | `redis-cli ping` |
| 3 | MinIO | `minio/minio:latest` | `127.0.0.1:9000` (API), `:9001` (Console) | 512 MB / 0.5 CPU | `/minio/health/live` |
| 4 | OpenBao 2.6.0 | `openbao/openbao:2.6.0` | `127.0.0.1:8200` | 512 MB / 0.5 CPU | `openbao status` (sealed=false) |
| 5 | Keycloak 26.0 | `quay.io/keycloak/keycloak:26.0` | `127.0.0.1:8080` | 1024 MB / 0.5 CPU | port check |
| 6 | Gitea 1.23.4 | `gitea/gitea:1.23.4-rootless` | `127.0.0.1:3000` (Web), `:2222`→222 (SSH) | 1024 MB / 0.5 CPU | `wget -qO- http://localhost:3000/` |
| 7 | SearXNG | `searxng/searxng:latest` | `127.0.0.1:8081` | 512 MB / 0.5 CPU | `wget -qO- http://localhost:8081/` |
| 8 | NSQD | `nsqio/nsq:latest` | `127.0.0.1:8071` (API), `:8072` (lookup) | 256 MB / 0.25 CPU | `wget -qO- http://localhost:8072/ping` |
| 9 | LightSerp API | `mkanavi/lightserp-api:latest` | `127.0.0.1:3071` | 1024 MB / 1 CPU | port check `/health` |
| 10 | LightSerp WebUI | `mkanavi/lightserp-webui:latest` | `127.0.0.1:3070` | 512 MB / 0.5 CPU | `hc_webui.js` |
| 11 | PageZen | `mkanavi/pagezen:latest` | `127.0.0.1:8076` | 256 MB / 0.25 CPU | port check |

## Architecture

```
[Cloudflare Tunnel] → [Nginx Reverse Proxy] → [Docker Services on iacgenie-network]
                                                        │
                                              ┌─────────┼─────────┐
                                              │         │         │
                                         [Postgres]  [Redis]  [MinIO]
                                              │         │         │
                                        [Keycloak]  [Gitea]  [OpenBao]
                                              │
                                        [LightSerp Stack]
                                        [SearXNG] [NSQD] [PageZen]
```

## Ingress

### Nginx Reverse Proxy

All services bound to `127.0.0.1` (loopback only). Nginx proxies external HTTPS traffic to internal ports.

| Hostname                 | Service          | Nginx → Container Port |
|--------------------------|------------------|------------------------|
| `app.iacgenie.com`       | LightSerp WebUI  | → `127.0.0.1:3070`    |
| `auth.iacgenie.com`      | Keycloak         | → `127.0.0.1:8080`    |
| `git.iacgenie.com`       | Gitea            | → `127.0.0.1:3000`    |
| `console.iacgenie.com`   | MinIO Console    | → `127.0.0.1:9001`    |
| `vault.iacgenie.com`     | OpenBao          | → `127.0.0.1:8200`    |
| `search.iacgenie.com`    | SearXNG          | → `127.0.0.1:8081`    |

### Cloudflare Tunnel

- **Service:** `cloudflared` (systemd)
- **Config:** `/etc/cloudflared/config.yml`
- **Purpose:** Exposes all `*.iacgenie.com` hostnames via Cloudflare Edge

### DNS Records

All hostnames use CNAME to `<account>.cfargotunnel.com` via Cloudflare Dashboard.

## Known Issues & Fixes

### Docker DNS Resolution
Docker daemon cannot resolve registry.docker.io on some networks. **Fix:** Add DNS to `daemon.json.j2`:
```json
"dns": ["8.8.8.8", "1.1.1.1"]
```

### OpenBao Storage Type
File storage is not suitable for production. **Fix:** Set `OPENBAO_STORAGE_TYPE: raft` in compose template.

### OpenBao Healthcheck
Self-signed TLS certs cause curl to fail. **Fix:** Use `curl -k` flag and check for both `sealed: false` and `initialized: true`.

### UFW Policy
UFW 2.x+ uses `allow` instead of `accept` for UFW module `policy` field. **Fix:** Changed `policy: accept` → `policy: allow`.

### Gitea Rootless Image
Rootless image runs as UID 100, GID 1000. **Fix:** Data directory owner must be `100:1000`.

### SearXNG
SearXNG requires `SEARXNG_SECRET` env var. Must be generated with: `python3 -c "import secrets; print(secrets.token_hex(32))"`

## Infrastructure Services

- **Nginx:** Reverse proxy at `/etc/nginx/sites-enabled/`
- **Cloudflare Tunnel:** systemd service at `/etc/systemd/system/cloudflared.service`
- **Fail2ban:** SSH protection, max 3 retries
- **UFW:** Ports 22, 80, 443 allowed
- **NTP:** Synced to `time.cloudflare.com`

## Backup

### Automated Backups

| Service | Script | Schedule | Retention | Location |
|---------|--------|----------|-----------|----------|
| OpenBao Raft | `/opt/backup/backup_openbao.py` | Every 6h | 30 days | `/opt/backup/` |
| PostgreSQL | `playbooks/backup.yml --tags postgresql` | Daily 02:00 | 14 days | `/opt/backup/pg/` |
| MinIO | `playbooks/backup.yml --tags minio` | Daily 03:00 | 7 days | `/opt/backup/minio/` |
| Gitea repos | `playbooks/backup.yml --tags gitea` | Weekly Sun 04:00 | 4 weeks | `/opt/backup/gitea/` |

### Manual Backup Commands

```bash
# OpenBao
cd /opt/backup && python3 backup_openbao.py

# PostgreSQL
cd ~/projects/iacgenie-deploy && ansible-playbook playbooks/backup.yml --tags postgresql

# MinIO
mc mirror iacgenie/iacgenie-lightserp /opt/backup/minio/iacgenie-lightserp/

# Gitea
cd ~/projects/iacgenie-deploy && ansible-playbook playbooks/backup.yml --tags gitea
```

> **Full backup & restore procedures:** See [BACKUP.md](../BACKUP.md) in the unified infra repo.

## Docker Compose File

**Primary location:** `/home/mkanavi/docker/iacgenie/docker-compose-unified.yml`  
**Generated by:** `docker-compose-generator` role (Ansible)  
**Do not edit manually** — run `ansible-playbook playbooks/services.yml` to regenerate.

### Docker Volume Paths

| Volume | Mount Path |
|--------|-----------|
| `postgres_data` | `/home/mkanavi/docker/iacgenie/postgres_data` |
| `redis_data` | `/home/mkanavi/docker/iacgenie/redis_data` |
| `minio_data` | `/home/mkanavi/docker/iacgenie/minio_data` |
| `openbao_data` | `/home/mkanavi/docker/iacgenie/openbao_data` |
| `openbao_raft` | `/home/mkanavi/docker/iacgenie/openbao_raft` |
| `gitea_data` | `/home/mkanavi/docker/iacgenie/gitea_data` |
| `keycloak_data` | `/home/mkanavi/docker/iacgenie/keycloak_data` |

### systemd Service

```bash
# Start all services
sudo systemctl start lightserp

# Check status
sudo systemctl status lightserp

# View logs
sudo journalctl -u lightserp -f
```

## Secrets

All secrets stored in OpenBao at `iacgenie/` path. Environment variables in `.env` reference OpenBao secrets:
- `MINIO_ROOT_PASSWORD`
- `PG_ROOT_PASSWORD`
- `KEYCLOAK_ADMIN_PASSWORD`
- `KC_DB_PASSWORD`
- `GITEA_DB_PASSWORD`
- `SEARXNG_SECRET_KEY`
- `LIGHTSERP_API_SECRET`
- SMTP credentials

## Update Workflow

1. Make playbook/template changes
2. Test locally with `ansible-playbook --check`
3. Run `ansible-playbook --diff` to review changes
4. Execute `ansible-playbook playbooks/services.yml`
5. Verify with `ansible-playbook playbooks/validate-services.yml`
6. Commit and push changes to this repository

## Troubleshooting

### Containers Exited After Docker Restart

```bash
# Check systemd service (preferred)
sudo systemctl restart lightserp

# Or manual compose restart
cd /home/mkanavi/docker/iacgenie && docker compose up -d
```

### OpenBao Sealed

```bash
# Unseal (3 of 5 keys required — keys stored OFF-VM in password manager)
docker exec iacgenie_openbao openbao unseal <key>
docker exec iacgenie_openbao openbao unseal <key>
docker exec iacgenie_openbao openbao unseal <key>

# Verify
docker exec iacgenie_openbao openbao status
```

### LightSerp Build Failure

LightSerp images are built locally from the LightSerp repo:

```bash
cd ~/LightSerp && docker compose build
docker tag mkanavi/lightserp-api:latest mkanavi/lightserp-api:latest
docker tag mkanavi/lightserp-webui:latest mkanavi/lightserp-webui:latest
docker tag mkanavi/pagezen:latest mkanavi/pagezen:latest
```

### Cloudflare Tunnel Inactive

```bash
sudo systemctl restart cloudflared
sudo systemctl status cloudflared  # verify active
```

### Port Conflicts

All services are bound to `127.0.0.1` only. If a host port is occupied:

```bash
# Find what's using the port
sudo lsof -i :3071

# Edit the generated compose file and change the host port
# Then re-run: ansible-playbook playbooks/services.yml
```

### Nginx Config Reload

```bash
sudo nginx -t && sudo systemctl reload nginx
```
