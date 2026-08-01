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

| Service          | Image                        | Ports          | Status  |
|------------------|------------------------------|----------------|---------|
| PostgreSQL 15    | postgres:15-alpine           | 127.0.0.1:5432 | healthy |
| Redis 7          | redis:7-alpine               | 127.0.0.1:6379 | healthy |
| MinIO            | minio/minio:latest           | 127.0.0.1:9000 | healthy |
| OpenBao 2.6.0    | openbao/openbao:2.6.0        | 127.0.0.1:8200 | healthy |
| Keycloak 26.0    | quay.io/keycloak/keycloak:26.0 | 127.0.0.1:8080 | healthy |
| Gitea 1.23.4     | gitea/gitea:1.23.4-rootless  | 127.0.0.1:3000 | healthy |
| SearXNG          | searxng/searxng:latest       | 127.0.0.1:8080 | healthy |
| NSQD             | nsqio/nsq:latest             | 127.0.0.1:4150 | healthy |
| LightSerp API    | mkanavi/lightserp-api:latest | 127.0.0.1:8000 | healthy |
| LightSerp WebUI  | mkanavi/lightserp-webui:latest | 127.0.0.1:3001 | healthy |
| PageZen          | mkanavi/pagezen:latest       | 127.0.0.1:8081 | healthy |

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

| Hostname                 | Service          | Nginx Port |
|--------------------------|------------------|------------|
| app.iacgenie.com         | LightSerp WebUI  | 3001       |
| auth.iacgenie.com        | Keycloak         | 8080       |
| git.iacgenie.com         | Gitea            | 3000       |
| console.iacgenie.com     | MinIO            | 9001       |
| vault.iacgenie.com       | OpenBao          | 8200       |
| search.iacgenie.com      | SearXNG          | 8080       |

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

Backup playbook available via `playbooks/backup.yml`. Configured to backup:
- PostgreSQL database (`lightsrp`)
- MinIO buckets (`iacgenie-lightserp`)
- Gitea repositories
- OpenBao secret store

## Docker Compose File

Generated at `/home/mkanavi/iacgenie-unified-infra/docker-compose.yml` by the `docker-compose-generator` role. Do not edit manually.

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
Run: `cd /home/mkanavi/iacgenie-unified-infra && docker compose up -d`

### OpenBao Sealed
Run: `docker exec iacgenie_openbao openbao unseal <key>` (3 of 5 keys required)

### LightSerp Build Failure
LightSerp images are built locally from the LightSerp repo. Rebuild with:
```bash
cd ~/LightSerp && docker compose build
docker tag mkanavi/lightserp-api:latest mkanavi/lightserp-api:latest
docker tag mkanavi/lightserp-webui:latest mkanavi/lightserp-webui:latest
docker tag mkanavi/pagezen:latest mkanavi/pagezen:latest
```

### Cloudflare Tunnel Inactive
After DNS/cert changes: `sudo systemctl restart cloudflared`
