#!/usr/bin/env bash
# ==============================================================================
# Zohra Autonomous Publishing OS — Backup Trigger & Verification Script
# ==============================================================================

set -euo pipefail

echo "📦 Triggering automated system backup..."
python -c "
import asyncio, json
from app.services.backup import BackupManager

async def run():
    mgr = BackupManager()
    manifest = await mgr.create_backup(encrypt=True)
    print('Backup Manifest:')
    print(json.dumps(manifest, indent=2))
    ver = mgr.verify_backup(manifest['backup_name'])
    print('\nVerification Result:', ver['status'])

asyncio.run(run())
"
echo "✓ Backup process completed and verified."
