@echo off
title Maple AI Companion Agent 启动器
cd /d "%~dp0"

echo ========== Maple Agent Launcher ==========
echo 正在检查环境并启动服务,请稍候...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Maple Agent 启动.ps1"
set "EXITCODE=%errorlevel%"

if not "%EXITCODE%"=="0" (
    echo.
    echo [错误] 启动失败,请查看上方提示或 launcher\launcher.log
    pause
) else (
    echo.
    echo [完成] 服务已启动,浏览器即将打开。本窗口将在 3 秒后自动关闭。
    timeout /t 3 /nobreak >nul
)
