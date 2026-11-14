# ZOHRA DISASTER RECOVERY & INCIDENT RUNBOOK

## 1. Objectives & Targets

- **Recovery Point Objective (RPO)**: < 24 Hours (daily automated encrypted backups with remote copy).
- **Recovery Time Objective (RTO)**: < 30 Minutes for server rebuild and sandbox-verified restoration.

---

## 2. Emergency Kill-Switch Activation

When anomalous publishing, runaway spending, or external security incidents occur:

```bash
# Via API:
curl -X POST http://localhost:8000/api/v1/system/autonomy/pause \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Or via Command Center UI:
Click the red "EMERGENCY PAUSE" button in the top navigation header.
```

**Guarantees**:
- Halts all new autonomous drafting, verification, and publishing operations immediately.
- Safely completes currently active database transactions.
- Never leaves partial or corrupted WordPress posts.

---

## 3. Incident Scenarios & Procedures

### Scenario A: Server / VPS Loss
1. Provision new server (Ubuntu 24.04 LTS or Debian 12).
2. Clone repository: `git clone <repo_url> zohra-publisher`.
3. Restore `.env.production` from offline vault / 1Password.
4. Retrieve latest encrypted backup file: `zohra_backup_YYYYMMDD_HHMMSS.enc`.
5. Run sandbox restore test:
   ```bash
   ./scripts/restore.sh backups/zohra_backup_YYYYMMDD_HHMMSS.enc
   ```
6. Start production stack:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```
7. Verify health:
   ```bash
   curl http://localhost/health/ready
   ```

### Scenario B: Database Corruption
1. Activate Emergency Pause: `POST /api/v1/operations/autonomy/pause`.
2. Stop application workers to prevent new database writes:
   ```bash
   docker compose -f docker-compose.prod.yml stop api worker-general worker-publishing worker-analytics worker-optimization
   ```
3. Run restore script to isolated sandbox, then confirm apply:
   ```bash
   ./scripts/restore.sh backups/zohra_backup_latest.enc
   ```
4. Restart application services:
   ```bash
   docker compose -f docker-compose.prod.yml start api worker-general worker-publishing worker-analytics worker-optimization
   ```
5. Resume autonomy after verification: `POST /api/v1/operations/autonomy/resume`.

### Scenario C: Redis Loss / Cache Eviction
- Redis in Zohra stores message queues and distributed locks, NOT durable state.
- Durable state resides in PostgreSQL.
- Restart Redis:
  ```bash
  docker compose -f docker-compose.prod.yml restart redis
  ```
- Workers automatically reconnect via Celery reconnection backoff.

### Scenario D: Compromised WordPress / External API Credentials
1. Pause autonomy immediately: `POST /api/v1/operations/autonomy/pause`.
2. In WordPress Admin, revoke existing Application Password.
3. Generate new Application Password in WordPress.
4. Update encrypted secret in Zohra via API:
   ```bash
   curl -X POST http://localhost:8000/api/v1/secrets/rotate \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"key_name": "WP_APPLICATION_PASSWORD", "value": "NEW_GENERATED_PASSWORD", "site_id": "<SITE_UUID>"}'
   ```
5. Run WordPress connection test before resuming autonomy.

### Scenario E: Mass Publishing Anomaly / Erroneous Content
1. Pause autonomy immediately: `POST /api/v1/operations/autonomy/pause`.
2. Identify affected posts via published registry:
   ```bash
   curl -X GET "http://localhost:8000/api/v1/operations/pipeline?site_id=<SITE_UUID>" \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```
3. Mark status in WordPress as `draft` or `private`.
4. Audit root cause in `security_events` and `alerts` tables.
