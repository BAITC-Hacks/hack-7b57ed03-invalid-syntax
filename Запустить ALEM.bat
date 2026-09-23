@echo off
cd /d "%~dp0"
py -3 launch_desktop.py
if errorlevel 1 pause
