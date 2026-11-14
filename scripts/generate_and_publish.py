"""
Zohra — Forwarder for AI Article Generator & Publisher.
Allows running from root workspace folder: c:\\Users\\dell\\Desktop\\Zohra - Blog AI
"""

import subprocess
import sys
from pathlib import Path

publisher_dir = Path(__file__).resolve().parent.parent / "zohra-publisher"
target_script = publisher_dir / "scripts" / "generate_and_publish.py"

if not target_script.exists():
    print(f"Error: Could not locate target script at {target_script}")
    sys.exit(1)

cmd = [sys.executable, str(target_script)] + sys.argv[1:]
result = subprocess.run(cmd, cwd=str(publisher_dir))
sys.exit(result.returncode)
