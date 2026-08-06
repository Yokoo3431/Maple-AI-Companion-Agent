# ============================================================
#  Maple AI Companion Agent - 环境初始化脚本 (setup.ps1)
#  用途:换电脑后一键恢复环境
#    git clone <repo> -> 运行本脚本 -> 环境自动恢复
# ============================================================
param(
    [string]$ProjectRoot = "",   # 项目根目录(默认取脚本上级)
    [string]$VenvDir = "",       # venv 目录(默认 $ProjectRoot\.venv)
    [switch]$CheckOnly,          # 只检查,不创建 venv / 不安装依赖
    [switch]$VenvOnly            # 只创建 venv,不安装依赖(测试用)
)

$ErrorActionPreference = "Stop"

# 输出统一 UTF-8,避免中文乱码
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # 某些重定向场景不可设置,忽略
}

if (-not $ProjectRoot) { $ProjectRoot = Split-Path -Parent $PSScriptRoot }
if (-not $VenvDir) { $VenvDir = Join-Path $ProjectRoot ".venv" }
$venvPython = Join-Path $VenvDir "Scripts\python.exe"

function Write-Step {
    param([string]$Message)
    Write-Host "[setup] $Message"
}

function Find-RealPython {
    $candidates = @()
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) { $candidates += $pythonCmd.Source }
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) { $candidates += $pyCmd.Source }
    $programPython = Get-ChildItem (Join-Path $env:LOCALAPPDATA "Programs\Python") -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending
    foreach ($dir in $programPython) { $candidates += (Join-Path $dir.FullName "python.exe") }

    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate)) { continue }
        $versionOut = & $candidate -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $versionOut -match '^(\d+)\.(\d+)') {
            return @{ Path = $candidate; Version = $versionOut.Trim() }
        }
    }
    return $null
}

Write-Step "========== Maple AI Companion Agent 环境初始化 =========="
Write-Step "项目目录: $ProjectRoot"

# ---- 1. 检查 Python >= 3.11 ----
$python = Find-RealPython
if (-not $python) {
    Write-Host "[setup] 错误: 未检测到可用的 Python。请先安装 Python 3.11+ (https://www.python.org/downloads/) 后重试。"
    exit 1
}
$versionParts = $python.Version -split '\.'
$versionOk = ([int]$versionParts[0] -gt 3) -or ([int]$versionParts[0] -eq 3 -and [int]$versionParts[1] -ge 11)
if (-not $versionOk) {
    Write-Host "[setup] 错误: Python 版本过低(当前 $($python.Version)),需要 3.11 或更高。"
    exit 1
}
Write-Step "Python 版本检查通过: $($python.Version) ($($python.Path))"

# ---- 2. venv 检测 / 创建 ----
if (Test-Path -LiteralPath $venvPython) {
    Write-Step "venv 已存在: $VenvDir"
} elseif ($CheckOnly) {
    Write-Host "[setup] 错误: 未找到 venv($VenvDir)。CheckOnly 模式下跳过创建,请完整运行 setup.ps1。"
    exit 1
} else {
    Write-Step "创建 venv: $VenvDir"
    & $python.Path -m venv $VenvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPython)) {
        Write-Host "[setup] 错误: venv 创建失败。"
        exit 1
    }
    Write-Step "venv 创建完成"
}

if ($VenvOnly) {
    Write-Step "VenvOnly 模式完成(仅创建 venv,跳过依赖安装)。"
    exit 0
}

# ---- 3. 安装 / 检测依赖 ----
if ($CheckOnly) {
    & $venvPython -c "import fastapi, uvicorn, jinja2, pydantic" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[setup] 错误: 依赖缺失,请完整运行 setup.ps1 安装依赖。"
        exit 1
    }
    Write-Step "依赖检查通过"
} else {
    Write-Step "安装依赖 requirements.txt + requirements-dev.txt ..."
    & $venvPython -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) { Write-Host "[setup] 错误: pip 升级失败。"; exit 1 }
    & $venvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt") -r (Join-Path $ProjectRoot "requirements-dev.txt")
    if ($LASTEXITCODE -ne 0) { Write-Host "[setup] 错误: 依赖安装失败。"; exit 1 }
    Write-Step "依赖安装完成"
}

# ---- 4. 创建必要目录 ----
foreach ($dirName in @("logs", "sessions", "knowledge", "config")) {
    $dirPath = Join-Path $ProjectRoot $dirName
    if (-not (Test-Path -LiteralPath $dirPath)) {
        New-Item -ItemType Directory -Path $dirPath -Force | Out-Null
    }
}
Write-Step "必要目录已就绪: logs/ sessions/ knowledge/ config/"

# ---- 5. 生成 .env(仅从模板复制,不写真实 API Key) ----
$envExample = Join-Path $ProjectRoot ".env.example"
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path -LiteralPath $envFile) {
    Write-Step ".env 已存在,跳过(不覆盖,不写入真实 API Key)"
} elseif (Test-Path -LiteralPath $envExample) {
    Copy-Item -LiteralPath $envExample -Destination $envFile
    Write-Step ".env 已从 .env.example 生成(真实 API Key 请自行填写)"
} else {
    Write-Host "[setup] 提示: 未找到 .env.example,跳过 .env 生成。"
}

# ---- 6. 运行 doctor 自检 ----
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
Write-Step "运行 python -m maple_agent doctor ..."
& $venvPython -m maple_agent doctor
if ($LASTEXITCODE -ne 0) {
    Write-Host "[setup] 错误: doctor 检查未通过,请查看上方输出或 logs\ 日志。"
    exit 1
}

Write-Step "环境初始化完成,现在可以双击 launcher\Maple Agent 启动.bat 使用了。"
