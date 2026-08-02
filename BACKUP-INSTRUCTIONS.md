# Backup & Restore Instructions for IacGenie Infrastructure Teardown/Rebuild

**Date:** 2026-08-02  
**Backup Location:** `/opt/backup/pre-teardown-20260802/`  
**Total Size:** 193MB

---

## What Was Backed Up

| File/Directory | Size | Contents |
|---|---|---|
| `gitea-data.tar.gz` | 144MB | All Gitea repositories, issues, configs |
| `openbao-raft/` | 47MB | OpenBao Raft consensus data + vault.db |
| `pg-dump.sql` | 868KB | Full PostgreSQL dump (all databases) |
| `letsencrypt-archive/` | 52KB | Historical TLS certificate versions |
| `letsencrypt-live/` | 24KB | Current TLS certificates for active domains |
| `openbao-data/` | 20KB | OpenBao configuration and audit logs |
| `docker-compose-unified.yml` | 12KB | Pre-teardown Docker Compose file |
| `minio-data.tar.gz` | 8KB | MinIO object storage data |
| `iacgenie-deploy/` | 1.6MB | Ansible playbooks (with all 14 risk fixes) |
| `cloudflared-config.yml` | 4KB | Cloudflare Tunnel configuration |

---

## Pre-Teardown Checklist (Before Destructive Operations)

### ✅ Completed
- [x] PostgreSQL full dump → `pg-dump.sql`
- [x] MinIO data → `minio-data.tar.gz`
- [x] OpenBao Raft data → `openbao-raft/`
- [x] OpenBao configuration → `openbao-data/`
- [x] Gitea repositories → `gitea-data.tar.gz`
- [x] TLS certificates → `letsencrypt-live/` + `letsencrypt-archive/`
- [x] Cloudflare tunnel config → `cloudflared-config.yml`
- [x] Docker Compose file → `docker-compose-unified.yml`
- [x] Ansible playbooks → `iacgenie-deploy/`

### 🔴 CRITICAL — Must Save Manually
- [ ] **OpenBao Unseal Keys** (5 keys, stored OFF-VM in password manager)
- [ ] **Cloudflare Account Token** (in `~/.cloudflared/*.json` or stored in CF dashboard)
- [ ] **SMTP Credentials** (SMTP2GO API key — check Ansible `group_vars/all.yml`)
- [ ] **LightSerp Docker Images** (tagged locally: `mkanavi/lightserp-api:latest`, etc.)

---

## Teardown Commands

> ⚠️ **WARNING: This is destructive.** All Docker containers, volumes, and service configurations will be removed.

```bash
# 1. Stop all Docker services
cd /home/mkanavi/docker/iacgenie/
docker compose -f docker-compose-unified.yml down -v
# The -v flag removes all named volumes!

# 2. Stop systemd services
sudo systemctl stop cloudflared
sudo systemctl stop nginx

# 3. Remove old configs (clean slate)
sudo rm -f /etc/cloudflared/config.yml
sudo rm -f /etc/cloudflared/*.json
sudo rm -f /etc/nginx/conf.d/iacgenie.conf
sudo rm -f /etc/nginx/conf.d/iacgenie-unified.conf*

# 4. Remove old docker-compose
rm -f /home/mkanavi/docker/iacgenie/docker-compose-unified.yml
rm -f /home/mkanavi/docker/iacgenie/.env
```

---

## Restore from Backup

### Option A: Full Rebuild with Ansible (Recommended)

After cleanup, re-run the Ansible playbooks to rebuild everything:

```bash
# 1. Navigate to playbook directory
cd /home/mkanavi/projects/iacgenie-deploy

# 2. Run bootstrap (system setup + Docker)
ansible-playbook playbooks/bootstrap.yml -i inventory/hosts.ini

# 3. Deploy services (containers + nginx + cloudflared)
ansible-playbook playbooks/services.yml -i inventory/hosts.ini

# 4. Validate
ansible-playbook playbooks/validate-services.yml -i inventory/hosts.ini
```

### Option B: Restore from Pre-Teardown Backup

If the Ansible playbook fails, restore from the backup files:

```bash
BACKUP=/opt/backup/pre-teardown-20260802

# Restore Docker Compose
cp $BACKUP/docker-compose-unified.yml /home/mkanavi/docker/iacgenie/
cp $BACKUP/.env /home/mkanavi/docker/iacgenie/ 2>/dev/null || true

# Restore MinIO
tar xzf $BACKUP/minio-data.tar.gz -C /home/mkanavi/docker/iacgenie/minio_data/

# Restore Gitea
tar xzf $BACKUP/gitea-data.tar.gz -C /home/mkanavi/docker/iacgenie/gitea_data/

# Restore OpenBao Raft
cp -r $BACKUP/openbao-raft /home/mkanavi/docker/iacgenie/openbao_raft/
chown -R mkanavi:mkanavi /home/mkanavi/docker/iacgenie/openbao_raft/

# Restore PostgreSQL
docker exec -i iacgenie-postgres psql -U postgres < $BACKUP/pg-dump.sql

# Restore TLS certs
sudo cp -r $BACKUP/letsencrypt-live /etc/letsencrypt/
sudo cp -r $BACKUP/letsencrypt-archive /etc/letsencrypt/ 2>/dev/null || true

# Restore Cloudflare config
sudo cp $BACKUP/cloudflared-config.yml /etc/cloudflared/

# Restore Ansible playbooks
cp -r $BACKUP/iacgenie-deploy /home/mkanavi/projects/iacgenie-deploy
```

---

## Post-Restore Steps

1. **Verify all services are running:**
   ```bash
   docker compose -f /home/mkanavi/docker/iacgenie/docker-compose-unified.yml ps
   sudo systemctl status cloudflared
   sudo systemctl status nginx
   ```

2. **Check Cloudflare Tunnel connectivity:**
   ```bash
   curl -s https://auth.iacgenie.com/health | jq
   ```

3. **Verify Nginx reverse proxy:**
   ```bash
   sudo nginx -t
   ```

4. **Test service endpoints via Cloudflare Tunnel:**
   - auth.iacgenie.com → Keycloak
   - app.iacgenie.com → LightSerp WebUI
   - api.iacgenie.com → LightSerp API
   - search.iacgenie.com → SearXNG
   - git.iacgenie.com → Gitea

5. **Regenerate Let's Encrypt certs for all subdomains:**
   ```bash
   # If HTTP-01 challenge works:
   sudo certbot renew --dry-run
   
   # If DNS-01 challenge (wildcard):
   # Re-run the certbot DNS challenge for *.iacgenie.com
   ```

---

## Recovery Priority Order

If a partial restore is needed, follow this priority:

1. **OpenBao Raft** → OpenBao must be restored FIRST because all other services depend on it for secrets
2. **PostgreSQL** → Keycloak, Gitea, and all apps need the database
3. **MinIO** → LightSerp needs object storage
4. **Gitea** → Repository data
5. **TLS Certificates** → Required before services can receive HTTPS traffic
6. **Cloudflare Tunnel** → Required for external access
7. **Docker Compose** → All containers

---

## Contact / Support

- **OpenBao unseal keys:** Stored OFF-VM in password manager (1Password/Bitwarden)
- **Cloudflare account:** https://dash.cloudflare.com → Tunnels
- **DNS records:** CNAMEs pointing to tunnel URL in Cloudflare Dashboard
