# X.1-X.6 Validation & Fixes — Final Report

**Date**: 2026-08-01
**VM**: 192.168.0.118 (iacgenie-server)
**Playbook**: `playbooks/site.yml`
**Branch**: Default/Production

---

## Task Summary

| Task | Status | Result |
|------|--------|--------|
| X.1 Dry-run site.yml | ✅ | `ok=75, changed=10, failed=0` |
| X.2 Bootstrap role | ✅ | `ok=42, changed=0, failed=0` |
| X.3 Service roles (check mode) | ✅ | 0 failures across 12 roles |
| X.4 Full end-to-end run (initial) | ❌ | `failed=1` (searxng restart) |
| X.4 Full end-to-end (fixed) | ✅ | `ok=105, changed=21, failed=0` |
| X.4 Full end-to-end (final) | ✅ | `ok=96, changed=0, failed=0` |
| X.5 Idempotency check | ✅ | `ok=96, changed=0, failed=0` |
| X.6 Documentation | ✅ | This file |

---

## Bugs Found & Fixed

### Bug 1: SearXNG Handler — Container Name Mismatch
**Symptom**: `docker compose -p iacgenie restart searxng` → `no such service: searxng`  
**Root cause**: Running service name is `lightserp-searxng` but playbook referenced `searxng`  
**Fix**: Updated handler and verify task in `roles/searxng/` to use `lightserp-searxng`

### Bug 2: NSQD & PageZen — Same Service Name Mismatch
**Symptom**: Potential failure if `.env` files changed and triggered handlers  
**Fix**: Updated `roles/nsqd/` and `roles/pagezen/` handlers/tasks to use `lightserp-nsqd` and `lightserp-pagezen`

### Bug 3: SSH Key Placeholder
**Symptom**: SSH public keys never applied — `REPLACE_WITH_ACTUAL_SSH_PUBLIC_KEY` filtered out by `when` guard  
**Fix**: Replaced placeholder with actual key from `~/.ssh/newvm_key.pub`

### Bug 4: `.env` Idempotency — All 10 Services Wrote Same File
**Symptom**: Every service role wrote to `/home/mkanavi/iacgenie-unified-infra/.env`, overwriting previous roles. Each subsequent role saw the file as "changed" because another role had just written different content. Result: `changed=21` every run, even after all services were deployed.  
**Fix**: Architectural change — each service now deploys to its own `.env.<service>` file (e.g., `.env.postgres`, `.env.redis`). The `docker-compose-generator` role now merges all `.env.*` files into the unified `.env` file using a shell script that diff-compares before writing.

### Bug 5: `docker compose` Without `-f` Flag
**Symptom**: "no configuration file provided: not found" when CWD doesn't contain docker-compose.yml  
**Fix**: Updated all `docker compose` commands in handlers and tasks to use `-f /home/mkanavi/iacgenie-unified-infra/docker-compose.yml`

### Bug 6: Role Ordering
**Symptom**: `docker-compose-generator` ran before service roles, so the merged `.env` didn't include service env vars yet.  
**Fix**: Moved `docker-compose-generator` to run AFTER all service roles in `playbooks/services.yml`

---

## Files Modified

| File | Change |
|------|--------|
| `inventory/group_vars/all.yml` | SSH key placeholder → actual key |
| `roles/searxng/handlers/main.yml` | `searxng` → `lightserp-searxng` |
| `roles/searxng/tasks/main.yml` | `searxng` → `lightserp-searxng` in verify task |
| `roles/nsqd/handlers/main.yml` | `nsqd` → `lightserp-nsqd` |
| `roles/nsqd/tasks/main.yml` | `nsqd` → `lightserp-nsqd` in verify task |
| `roles/pagezen/handlers/main.yml` | `pagezen` → `lightserp-pagezen` |
| `roles/pagezen/tasks/main.yml` | `pagezen` → `lightserp-pagezen` in verify task |
| `roles/postgresql/tasks/main.yml` | `.env` → `.env.postgres` |
| `roles/redis/tasks/main.yml` | `.env` → `.env.redis` |
| `roles/minio/tasks/main.yml` | `.env` → `.env.minio` |
| `roles/openbao/tasks/main.yml` | `.env` → `.env.openbao` |
| `roles/keycloak/tasks/main.yml` | `.env` → `.env.keycloak` |
| `roles/gitea/tasks/main.yml` | `.env` → `.env.gitea` |
| `roles/lightserp/tasks/main.yml` | `.env` → `.env.lightserp` |
| `roles/searxng/tasks/main.yml` | `.env` → `.env.searxng` |
| `roles/nsqd/tasks/main.yml` | `.env` → `.env.nsqd` |
| `roles/pagezen/tasks/main.yml` | `.env` → `.env.pagezen` |
| `roles/docker-compose-generator/tasks/main.yml` | Added `env-merge.yml` import |
| `roles/docker-compose-generator/tasks/env-merge.yml` | New: merge `.env.*` into `.env` |
| `roles/docker-compose-generator/handlers/main.yml` | Added `-f` flag to all `docker compose` commands |
| `roles/docker-compose-generator/tasks/deploy.yml` | Added `-f` flag to check task |
| `playbooks/services.yml` | Moved `docker-compose-generator` to end (after services) |

---

## Architecture Change: `.env` Files

### Before
```
All 10 service roles → /home/mkanavi/iacgenie-unified-infra/.env (single shared file)
```
Result: Last writer wins, idempotency broken.

### After
```
PostgreSQL → .env.postgres
Redis      → .env.redis
MinIO      → .env.minio
OpenBao    → .env.openbao
Keycloak   → .env.keycloak
Gitea      → .env.gitea
LightSerp  → .env.lightserp
SearXNG    → .env.searxng
NSQD       → .env.nsqd
PageZen    → .env.pagezen
                                  ↓ (merged by docker-compose-generator)
                     .env (unified, auto-loaded by Docker Compose)
```

---

## Verification Results

### All 11 Services Healthy
| Service | Container | Status |
|---------|-----------|--------|
| PostgreSQL | iacgenie-postgres | Up (healthy) |
| Redis | iacgenie-redis | Up (healthy) |
| MinIO | iacgenie-minio | Up (healthy) |
| OpenBao | iacgenie-openbao | Up (healthy) |
| Keycloak | iacgenie-keycloak | Up (healthy) |
| Gitea | iacgenie-gitea | Up (healthy) |
| LightSerp API | iacgenie-lightserp-api | Up (healthy) |
| LightSerp WebUI | iacgenie-lightserp-webui | Up (healthy) |
| SearXNG | iacgenie-searxng | Up (healthy) |
| NSQD | iacgenie-nsqd | Up (healthy) |
| PageZen | iacgenie-pagezen | Up (healthy) |

### Idempotency
- **First run**: `ok=96, changed=0, failed=0`
- **Second run** (idempotency): `ok=96, changed=0, failed=0`

### Skipped Tasks (4 total)
- Cloudflare verify + show (idempotent status checks)
- 2 more (service-specific)

---

## Logs
- Dry-run: `/tmp/x4-retry.txt`
- Final run 1: `/tmp/x4-final.txt`
- Final run 2: `/tmp/x4-final2.txt`
- Idempotency: `/tmp/x5-final.txt`
