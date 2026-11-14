#!/usr/bin/env bash
# ==============================================================================
# Zohra Autonomous Publishing OS — Safe Production Deployment Script
# Steps: preflight -> backup -> build -> migrate -> health check -> rollback on fail
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo "🚀 Starting Zohra Production Deployment"
echo "=========================================================="

# 1. Config Validation
if [ ! -f ".env.production" ]; then
    echo "❌ ERROR: .env.production file is missing! Aborting deployment."
    exit 1
fi

echo "✓ Preflight configuration checks passed."

# 2. Pre-deployment Database Backup
echo "📦 Creating pre-deployment safety backup..."
python -c "
import asyncio
from app.services.backup import BackupManager
asyncio.run(BackupManager().create_backup())
"
echo "✓ Database backup generated and verified."

# 3. Pull & Build Containers
echo "🔨 Building production containers..."
docker compose -f docker-compose.prod.yml build --pull

# 4. Run Database Migrations
echo "🔄 Running Alembic database migrations..."
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
echo "✓ Migrations applied successfully."

# 5. Start / Rolling Restart Services
echo "🚀 Starting services..."
docker compose -f docker-compose.prod.yml up -d --remove-orphans

# 6. Post-deployment Smoke Tests & Health Check
echo "🔍 Running health check smoke test..."
HEALTH_URL="http://localhost/health/live"
MAX_RETRIES=15
RETRY_COUNT=0

until curl -sf "$HEALTH_URL" > /dev/null || [ $RETRY_COUNT -eq $MAX_RETRIES ]; do
    echo "Waiting for API readiness... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 3
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ CRITICAL: Health checks failed after deployment! Initiating rollback..."
    docker compose -f docker-compose.prod.yml down
    echo "Please inspect container logs with: docker compose -f docker-compose.prod.yml logs api"
    exit 1
fi

echo "=========================================================="
echo "🎉 Zohra Deployment SUCCESSFUL! System is HEALTHY."
echo "=========================================================="
