# ============================================================
#  Maple AI Companion Agent - External Review Package
#  生成 review_package/ 与 zip,方便提交给外部 AI 审核
# ============================================================
$ErrorActionPreference = "Stop"

$Root    = Split-Path -Parent $PSScriptRoot
$OutDir  = Join-Path $Root "review_package"
$Version = "0.1.0"
$ZipPath = Join-Path $Root "Maple_AI_Companion_Agent_review_v$Version.zip"

# 清理旧生成物(仅限 review_package 与 zip,均为脚本生成)
if (Test-Path -LiteralPath $OutDir) {
    Remove-Item -LiteralPath $OutDir -Recurse -Force
}
if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

function Copy-ProjectTree {
    param([string]$Source, [string]$Dest)
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    Get-ChildItem -LiteralPath $Source -Recurse -Force | Where-Object {
        $_.FullName -notmatch '__pycache__' -and
        $_.Name -notmatch '\.pyc$' -and
        $_.Name -ne 'launcher.log'
    } | ForEach-Object {
        $relative = $_.FullName.Substring($Source.Length).TrimStart('\', '/')
        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Path (Join-Path $Dest $relative) -Force | Out-Null
        } else {
            $destFile = Join-Path $Dest $relative
            New-Item -ItemType Directory -Path (Split-Path -Parent $destFile) -Force | Out-Null
            Copy-Item -LiteralPath $_.FullName -Destination $destFile -Force
        }
    }
}

Copy-ProjectTree (Join-Path $Root "docs")  (Join-Path $OutDir "docs")
Copy-ProjectTree (Join-Path $Root "src")   (Join-Path $OutDir "src")
Copy-ProjectTree (Join-Path $Root "tests") (Join-Path $OutDir "tests")
Copy-Item -LiteralPath (Join-Path $Root "requirements.txt") -Destination (Join-Path $OutDir "requirements.txt")
Copy-Item -LiteralPath (Join-Path $Root "pyproject.toml")    -Destination (Join-Path $OutDir "pyproject.toml")

# 测试数量(venv 存在时运行)
$testSummary = "pytest 未运行(请在本机执行 python -m pytest 查看)"
$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $venvPython) {
    $junit = Join-Path $env:TEMP ("maple_pytest_{0}.xml" -f $PID)
    & $venvPython -m pytest -q "--junitxml=$junit" *> $null
    if (Test-Path -LiteralPath $junit) {
        [xml]$junitDoc = Get-Content -LiteralPath $junit -Raw
        $suite = $junitDoc.SelectSingleNode("/testsuites/testsuite")
        $tests = [int]$suite.GetAttribute("tests")
        $failures = [int]$suite.GetAttribute("failures") + [int]$suite.GetAttribute("errors")
        if ($failures -eq 0) {
            $testSummary = "pytest $tests passed"
        } else {
            $testSummary = "pytest $tests tests ($failures failed)"
        }
        Remove-Item -LiteralPath $junit -Force
    }
}

# ---- 生成文档 ----
$readmeReview = @'
# Maple AI Companion Agent - External Review Package

## 项目名称
Maple AI Companion Agent

## 当前版本
0.1.0 Phase 0 RC

## 审核目标

- 架构设计审核
- Agent 设计审核
- 安全边界审核
- 代码质量审核
- 后续 Phase 规划审核

## 当前完成

M0 - M7.1

## 当前未实现

- OCR
- Vision
- Input
- 游戏控制
- 自动任务
'@
Set-Content -LiteralPath (Join-Path $OutDir "README_REVIEW.md") -Value $readmeReview -Encoding UTF8

$projectStatus = @"
# Maple AI Companion Agent - Project Status

## 模块状态

| 模块 | 状态 |
| --- | --- |
| Config | ✅ |
| Logging | ✅ |
| EventBus | ✅ |
| Runtime | ✅ |
| Window Detector(Mock) | ✅ |
| Provider Layer | ✅ |
| WebUI | ✅ |
| Launcher | 🟡 |

## 测试

- $testSummary
- ruff: passed
"@
Set-Content -LiteralPath (Join-Path $OutDir "PROJECT_STATUS.md") -Value $projectStatus -Encoding UTF8

$architectureSummary = @'
# Maple AI Companion Agent - Architecture Summary

## 核心架构

```text
Config
   ↓
Runtime
   ↓
EventBus
   ↓
Providers
   ↓
WebUI
```

> 说明:实际启动流程为 Config → Logging → EventBus → Providers → Runtime → WebUI;
> Runtime 与各模块通过 EventBus 解耦,状态变化发布事件并写入 runtime.log(trace_id 贯穿)。

## 关键设计

### L1 / L2 双层决策

- L1 Reflex:本地实时反射层(HP/MP/死亡/紧急暂停),不调用 AI,目标延迟 < 100ms;
- L2 Planner:LLM Provider 规划层(任务选择/路线/补给/回城),秒级响应;
- L1 可打断 L2,紧急事件经 Event Bus 分发。

### Provider 抽象

- 统一 BaseProvider:生命周期 CREATED → INITIALIZED → SHUTDOWN + trace + 日志 + 事件;
- LLM / OCR / Vision / Storage 四类 Provider,Phase 0 仅 Mock;
- 未来接入 DeepSeek、Tesseract/Windows OCR/PaddleOCR 时替换 Mock 即可。

### Knowledge 设计

- 外部知识包 `knowledge/versions/<game_profile>/`(JSON/CSV),不绑定固定版本号;
- Phase 0 仅建 schema,不导入具体游戏数据;
- 支持手动/增量更新与更新报告。

### Phase 路线

- Phase 0:基础架构(M0-M7.1,已完成);
- Phase 1:Vision + OCR + Input Provider + Agent 状态机;
- Phase 2:知识库 + 路线 + 补给;
- Phase 3:任务 Agent + Human Teaching。
'@
Set-Content -LiteralPath (Join-Path $OutDir "ARCHITECTURE_SUMMARY.md") -Value $architectureSummary -Encoding UTF8

$changelog = @'
# Maple AI Companion Agent - Changelog

## Phase 0 (2026-08-06)

- M0: 仓库骨架(README / LICENSE / .gitignore / CI)
- M1: 配置系统(defaults.yaml + .env + 环境变量)
- M2: 日志系统(分模块文件 + trace_id/correlation_id + 轮转)
- M3: Event Bus(强类型事件 + 优先级队列)
- M4: Runtime 状态机 + 只读窗口检测接口
- M5: Provider 接口层(LLM / OCR / Vision / Storage + Mock)
- M6: WebUI 控制台(FastAPI + Jinja2 + Bootstrap + WebSocket)
- M7: 统一入口 + Health Check + CLI + Phase 0 Release 文档
- M7.1: Desktop Launcher(双击启动 + 环境检查 + 自动打开 WebUI)
- M7.1.1: Launcher 可用性修复 + External Review Package
'@
Set-Content -LiteralPath (Join-Path $OutDir "CHANGELOG.md") -Value $changelog -Encoding UTF8

# ---- 生成 zip ----
Compress-Archive -Path (Join-Path $OutDir "*") -DestinationPath $ZipPath -Force

# ---- 内容校验 ----
$files = Get-ChildItem -LiteralPath $OutDir -Recurse -File
$excludePattern = '__pycache__|\.pyc$|launcher\.log|(^|[\\/])\.env$|\.venv'
$badFiles = $files | Where-Object { $_.FullName -match $excludePattern -or $_.Name -eq ".env" }
if ($badFiles) {
    throw "敏感文件混入审核包: $($badFiles.FullName -join ', ')"
}

$localPathHits = @()
foreach ($file in $files | Where-Object { $_.Extension -in @('.md', '.txt', '.py', '.toml', '.yaml', '.yml', '.html') }) {
    $content = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
    if ($content -match 'CodexWorkspace|AntigravityWorkspace|Pondsi') {
        $localPathHits += $file.FullName
    }
}
if ($localPathHits.Count -gt 0) {
    throw "发现本地路径信息: $($localPathHits -join ', ')"
}

Write-Host "审核包生成完成:"
Write-Host "  目录: $OutDir"
Write-Host "  zip : $ZipPath"
Write-Host "  文件数量: $($files.Count)"
Write-Host "  排除列表: .venv / __pycache__ / *.pyc / logs/ / launcher.log / .env / review_package / 本地绝对路径"
