# ============================================================
#  Maple AI Companion Agent - Desktop Launcher (Phase 0)
#  双击同目录下的 "Maple Agent 启动.bat" 即可运行
# ============================================================
param(
    [switch]$NoOpen,    # 测试用:不自动打开浏览器
    [switch]$WaitAtEnd  # Debug 模式:结束后等待回车
)

$ErrorActionPreference = "Stop"

$LauncherDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot  = Split-Path -Parent $LauncherDir
$LauncherLog  = Join-Path $LauncherDir "launcher.log"

function Write-LauncherLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $LauncherLog -Value $line -Encoding UTF8
    Write-Host $Message
}

function Stop-LauncherFail {
    param([string]$Message)
    Write-LauncherLog "错误: $Message"
    if ($WaitAtEnd) {
        Write-Host ""
        Read-Host "Press Enter to exit"
    }
    exit 1
}

Write-LauncherLog "========== Maple Agent Launcher =========="
Write-LauncherLog "当前目录: $ProjectRoot"

# ---- 0. ExecutionPolicy 检查(被 bat 拦截时提示用户) ----
try {
    $policy = Get-ExecutionPolicy
    if ($policy -eq "Restricted") {
        Write-LauncherLog "检查结果: ExecutionPolicy=$policy(阻止脚本)。请使用 Maple Agent 启动.bat 启动(已自动绕过),或运行: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned"
    } else {
        Write-LauncherLog "检查结果: ExecutionPolicy=$policy(允许)"
    }
} catch {
    Write-LauncherLog "检查结果: ExecutionPolicy 检查失败: $($_.Exception.Message)"
}

# ---- 1. 检查 Python 环境 ----
$systemPython = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $systemPython = (Get-Command python -ErrorAction SilentlyContinue).Source
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $systemPython = & py -3 -c "import sys; print(sys.executable)" 2>$null
}
if (-not $systemPython) {
    Stop-LauncherFail "未检测到 Python 环境。请先安装 Python 3.11+ 后重试。"
}
Write-LauncherLog "Python路径: $systemPython"

# ---- 2. 检查项目 venv ----
$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    Stop-LauncherFail "未找到项目虚拟环境(.venv)。请运行 scripts\setup.ps1 完成安装。"
}
Write-LauncherLog "venv路径: $venvPython"

# ---- 3. 检查依赖 ----
& $venvPython -c "import fastapi, uvicorn, jinja2, pydantic" 2>$null
if ($LASTEXITCODE -ne 0) {
    Stop-LauncherFail "依赖缺失。请运行 .\.venv\Scripts\pip install -r requirements.txt"
}
Write-LauncherLog "检查结果: 依赖完整"

# ---- 4. 启动服务 ----
$webuiPort = 8080
$webuiUrl  = "http://127.0.0.1:$webuiPort"
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$startCommand = "$venvPython -m maple_agent start --host 127.0.0.1 --port $webuiPort"

Write-LauncherLog "启动命令: $startCommand"
Start-Process -FilePath $venvPython -ArgumentList @("-m", "maple_agent", "start", "--host", "127.0.0.1", "--port", "$webuiPort") -WorkingDirectory $ProjectRoot -WindowStyle Hidden

# ---- 5. 等待就绪并打开浏览器 ----
$ready = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $health = Invoke-RestMethod -Uri "$webuiUrl/api/health" -TimeoutSec 2
        if ($health.status -eq "ok") { $ready = $true; break }
    } catch {
        # 服务尚未就绪,继续等待
    }
}

if (-not $ready) {
    Stop-LauncherFail "服务启动超时,请查看 logs\ 目录下的日志。"
}

Write-LauncherLog "WebUI 地址: $webuiUrl"
if (-not $NoOpen) {
    try {
        Start-Process $webuiUrl
        Write-LauncherLog "已打开浏览器: $webuiUrl"
    } catch {
        Write-LauncherLog "提示: 自动打开浏览器失败,请手动访问 $webuiUrl"
    }
}
Write-LauncherLog "启动完成: 默认状态 READY(不会自动进入 RUNNING)。停止请在浏览器控制台点击 STOP。"

if ($WaitAtEnd) {
    Write-Host ""
    Read-Host "Press Enter to exit"
}
