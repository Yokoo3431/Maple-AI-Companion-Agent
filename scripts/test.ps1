# 运行测试
$ErrorActionPreference = "Stop"

if (Test-Path .\.venv\Scripts\python.exe) {
    & .\.venv\Scripts\python.exe -m pytest
} else {
    python -m pytest
}
