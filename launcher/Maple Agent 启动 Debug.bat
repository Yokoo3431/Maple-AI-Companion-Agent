@echo off
title Maple AI Companion Agent Æô¶¯Æ÷ (Debug)
cd /d "%~dp0"

echo ========== Maple Agent Launcher (Debug) ==========
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Maple Agent Æô¶¯.ps1" -WaitAtEnd

echo.
echo Press Enter to exit
pause >nul
