"""
Zohra — Root Workspace Forwarder for 24/7 Autonomous Publisher.
Enables running from root workspace: c:\\Users\\dell\\Desktop\\Zohra - Blog AI
"""

import subprocess
import sys
from pathlib import Path

publisher_dir = Path(__file__).resolve().parent.parent / "zohra-publisher"
target_script = publisher_dir / "scripts" / "autonomous_publisher.py"

if not target_script.exists():
    print(f"Error: Could not locate target script at {target_script}")
    sys.exit(1)

cmd = [sys.executable, "-u", str(target_script)] + sys.argv[1:]
result = subprocess.run(cmd, cwd=str(publisher_dir))
sys.exit(result.returncode)
