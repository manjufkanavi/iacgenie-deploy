# Phase 10.4 — Production Readiness (P3) — Completed
# Tasks 10.17 through 10.23:
#
# 10.17  Centralized logging — Loki + Promtail deployed
#         - Loki config at /home/mkanavi/docker/iacgenie/loki/loki-config.yaml
#         - Promtail config at /home/mkanavi/docker/iacgenie/promtail/promtail-config.yaml
#         - Grafana datasource configured
#
# 10.18  Monitoring stack — Prometheus + Grafana dashboards
#         - Prometheus scrape config updated
#         - Grafana datasource synced
#         - Service health dashboards configured
#
# 10.19  Backup & DR verification — All backup sources verified
#         - OpenBao raft snapshot verified
#         - Postgres backup verification
#         - Gitea backup verification
#         - rclone sync to GDrive confirmed
#         - RPO: 24h | RTO: 4h
#
# 10.20  TLS certificate automation — certbot auto-renewal
#         - certbot systemd timer installed
#         - DNS challenge renewal configured
#         - Monitoring for cert expiry added
#
# 10.21  Cloudflare tunnel redundancy — 2nd tunnel on separate port
#         - Primary tunnel: port 25901
#         - Secondary tunnel: port 25902
#         - Health checks on nginx:80
#
# 10.22  Service resource quotas — CPU/memory limits on all containers
#         - All 11 services have deploy.resources.limits
#         - OOM kill monitoring configured
#
# 10.23  Ansible idempotency hardening
#         - always_run guards on all conditionals
#         - Version pinning for all Docker images
#         - Compose file validation before deploy
#         - Drift detection playbook
