# IacGenie Ansible IAC Repository

> **Infrastructure as Code** — Deploy the IacGenie platform stack using Ansible playbooks on Ubuntu 24.04 VMs.

## Quick Start

```bash
# 1. Clone this repo
git clone https://git.iacgenie.com/mkanavi/iacgenie-deploy.git
cd iacgenie-deploy

# 2. Bootstrap the target VM
ansible-playbook playbooks/bootstrap.yml -i inventory/hosts

# 3. Deploy all services
ansible-playbook playbooks/services.yml -i inventory/hosts

# 4. Validate deployment
ansible-playbook playbooks/validate-services.yml -i inventory/hosts
```

## Target Environment

| Property | Value |
|----------|-------|
| VM Host | `192.168.0.118` |
| SSH User | `mkanavi` |
| OS | Ubuntu 24.04 |
| Docker | 29.x with Docker Compose v2 |
| Network | `iacgenie_network` (172.28.0.0/16) |

## Playbooks

| Playbook | Purpose |
|----------|---------|
| `bootstrap.yml` | System hardening, Docker, user setup, fail2ban, UFW |
| `services.yml` | Deploy all 11 Docker services (PostgreSQL, Redis, MinIO, OpenBao, Keycloak, Gitea, SearXNG, NSQD, LightSerp, PageZen) |
| `validate.yml` | Deployment validation checks |
| `validate-services.yml` | Health check validation against all containers |
| `backup.yml` | Backup management for all services |

## Architecture

```
[Cloudflare Tunnel] → [Nginx Reverse Proxy] → [11 Docker Services]
                                                     │
                                        ┌───────────┼───────────┐
                                        │           │           │
                                   [Data Layer]  [Auth Layer] [App Layer]
                                   Postgres  Redis    Keycloak    LightSerp
                                         MinIO   OpenBao   Gitea
                                         SearXNG  NSQD     PageZen
```

## Service Inventory

| # | Service | Container | Port |
|---|---------|-----------|------|
| 1 | PostgreSQL 15 | `iacgenie-postgres` | `127.0.0.1:5432` |
| 2 | Redis 7 | `iacgenie-redis` | `127.0.0.1:6379` |
| 3 | MinIO | `iacgenie-minio` | `127.0.0.1:9000/9001` |
| 4 | OpenBao 2.6.0 | `iacgenie-openbao` | `127.0.0.1:8200` |
| 5 | Keycloak 26.0 | `iacgenie-keycloak` | `127.0.0.1:8080` |
| 6 | Gitea 1.23.4 | `iacgenie-gitea` | `127.0.0.1:3000/2222` |
| 7 | SearXNG | `iacgenie-searxng` | `127.0.0.1:8081` |
| 8 | NSQD | `iacgenie-nsqd` | `127.0.0.1:8071/8072` |
| 9 | LightSerp API | `iacgenie-lightserp-api` | `127.0.0.1:3071` |
| 10 | LightSerp WebUI | `iacgenie-lightserp-webui` | `127.0.0.1:3070` |
| 11 | PageZen | `iacgenie-pagezen` | `127.0.0.1:8076` |

## Secrets

All secrets stored in **OpenBao** at `iacgenie/` path. Environment variables in `.env.example` reference OpenBao secrets.

## Roles

| Role | Service |
|------|---------|
| `common` | System hardening, UFW, fail2ban, NTP |
| `docker` | Docker + Docker Compose installation |
| `docker-compose-generator` | Generates Docker Compose from Jinja2 templates |
| `nginx` | Nginx reverse proxy configuration |
| `cloudflare_tunnel` | Cloudflare Tunnel agent |
| `postgresql` | PostgreSQL deployment |
| `redis` | Redis deployment |
| `minio` | MinIO S3 deployment |
| `openbao` | OpenBao deployment |
| `keycloak` | Keycloak IAM deployment |
| `gitea` | Gitea deployment |
| `searxng` | SearXNG deployment |
| `nsqd` | NSQD message queue |
| `lightserp` | LightSerp API + WebUI |
| `pagezen` | PageZen deployment |
| `backup` | Backup scripts and cron jobs |
| `monitoring` | Prometheus/Grafana (future) |

## Documentation

- **[DEPLOY.md](DEPLOY.md)** — Detailed deployment guide with troubleshooting
- **[BACKUP.md](../BACKUP.md)** — Backup and restore procedures
- **[INFRA-DESIGN.md](../INFRA-DESIGN.md)** — Full infrastructure design document

## Secrets Management

All secrets stored in **OpenBao** at `iacgenie/` path. Environment variables in `.env` reference OpenBao secrets:

```
iacgenie/minio_root_password
iacgenie/pg_root_password
iacgenie/kc_admin_password
iacgenie/kc_db_password
iacgenie/gitea_db_password
iacgenie/searxng_secret
iacgenie/lightserp_api_secret
```

## Update Workflow

1. Make playbook/template changes
2. Test: `ansible-playbook --check playbooks/services.yml`
3. Dry-run: `ansible-playbook --diff playbooks/services.yml`
4. Deploy: `ansible-playbook playbooks/services.yml`
5. Validate: `ansible-playbook playbooks/validate-services.yml`
6. Commit: `git add . && git commit -m "stage: update <service>"`

## Repo Layout

```
iacgenie-deploy/
├── ansible.cfg              # Ansible configuration
├── .vault_key               # Vault password file
├── .env.example             # Environment template
├── inventory/
│   └── hosts.yml            # Target host definitions
├── playbooks/
│   ├── site.yml             # Master playbook
│   ├── bootstrap.yml        # System preparation
│   ├── services.yml         # Service deployment
│   ├── validate.yml         # Validation checks
│   ├── validate-services.yml # Health verification
│   ├── backup.yml           # Backup management
│   └── scripts/             # Helper scripts
├── roles/                   # 21 Ansible roles
├── collections/             # Ansible Galaxy collections
├── requirements.txt         # Galaxy requirements
└── Makefile                 # Convenience targets
```

## Prerequisites

- Ubuntu 24.04 target VM
- SSH access with key-based auth
- 15GB+ RAM available
- Python 3 on target VM

## License

Internal use only.
