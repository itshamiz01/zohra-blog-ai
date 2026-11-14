@echo off
title Zohra Autonomous AI Publisher (24/7 Engine - 10 Min Cadence)
cd /d "%~dp0"
echo ========================================================================
echo   Starting Zohra 24/7 Hardcore Brainstorming & Publishing Engine
echo   Triggering every 10 minutes automatically
echo ========================================================================
python scripts\autonomous_publisher.py --interval 10
pause
