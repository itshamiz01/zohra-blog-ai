# ZOHRA OPERATIONAL RUNBOOKS

## Runbook 1: WordPress Integration Disconnected
- **Symptom**: Alert emitted: `[INTEGRATION] WordPress Connection Timed Out` or 401 Unauthorized.
- **Action**:
  1. Inspect error details in AlertManager: `GET /api/v1/alerts`.
  2. Verify target WordPress domain DNS and HTTPS certificate validity.
  3. Validate WordPress REST API reaches `/wp-json/wp/v2/posts`.
  4. If application password expired, rotate credentials via `POST /api/v1/secrets/rotate`.
  5. Publication jobs failing with retry will automatically resume once connectivity returns.

## Runbook 2: Search Console API Disconnected / Quota Exceeded
- **Symptom**: Alert emitted: `[INTEGRATION] GSC Data Ingestion Stale`.
- **Action**:
  1. Check if Google OAuth token expired or service account permissions were revoked on Search Console property.
  2. Check Google Cloud Console API quota usage.
  3. Articles remain published safely; analytics ingestion retries independently without halting the publishing pipeline.

## Runbook 3: LLM Provider Outage (OpenAI / Anthropic / Local)
- **Symptom**: Alert emitted: `[SYSTEM] LLM Provider Failure Rate Spike`.
- **Action**:
  1. Verify provider status page.
  2. The LLM abstraction automatically engages exponential backoff with jitter.
  3. If primary model fails, CostGovernor and model router switch to configured secondary provider.
  4. Critical verification never falls back to an unverified or low-capability model.

## Runbook 4: AI Budget Threshold Exceeded (CostGovernor)
- **Symptom**: Alert emitted: `[COST] Daily AI Budget at 90%` or `100%`.
- **Action**:
  1. At 75%: System enters `ECONOMY` mode. Exploratory research and low-priority polling are paused.
  2. At 100%: System enters `ESSENTIAL_ONLY` mode. All non-essential AI generation halts.
  3. Essential safety checks, critical rollbacks, and health monitoring remain functional.
  4. If higher spend is authorized, increase budget in `.env.production` or via API:
     ```json
     { "daily_cost_limit": 100.0 }
     ```

## Runbook 5: Queue Backlog After Downtime
- **Symptom**: Celery queue backlog accumulated during server maintenance.
- **Action**:
  1. DO NOT publish all queued articles simultaneously.
  2. Trigger backlog freshness revalidation:
     ```bash
     curl -X POST http://localhost:8000/api/v1/operations/backlog/revalidate \
       -H "Authorization: Bearer $ADMIN_TOKEN"
     ```
  3. Outdated breaking news drafts (> 48 hours old) are automatically transitioned to `stale_review` to prevent publishing obsolete information.

## Runbook 6: Dead-Letter Queue Management
- **Symptom**: Unrecoverable worker failures moved to dead-letter queue.
- **Action**:
  1. List dead-letter jobs: `GET /api/v1/operations/dead-letter`.
  2. Inspect task failure traceback.
  3. Fix underlying cause (e.g. external network timeout, missing image asset).
  4. Resubmit job safely: `POST /api/v1/operations/dead-letter/{job_id}/retry`.
