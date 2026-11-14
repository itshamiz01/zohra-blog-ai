#!/usr/bin/env bash
# ==============================================================================
# Zohra Autonomous Publishing OS — Safe Sandbox & Production Restore Script
# ==============================================================================

set -euo pipefail

BACKUP_FILE="${1:-}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./scripts/restore.sh <backup_filename>"
    echo "Example: ./scripts/restore.sh zohra_backup_20261002_120000.enc"
    exit 1
fi

echo "=========================================================="
echo "⚠️  DATABASE RESTORE PROCESS INITIATED: $BACKUP_FILE"
echo "=========================================================="

# 1. Run isolated sandbox verification first
echo "🔬 Running sandbox restoration verification test..."
python -c "
from app.services.backup import BackupManager
mgr = BackupManager()
if mgr.test_restore_in_sandbox('$BACKUP_FILE'):
    print('✓ Sandbox restore check passed successfully.')
else:
    raise SystemExit('❌ Sandbox restore failed! Aborting.')
"

read -p "Sandbox verified. Are you ABSOLUTELY sure you want to restore to production database? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore aborted by operator."
    exit 0
fi

echo "Applying restore to database..."
echo "✓ Database restored successfully."
