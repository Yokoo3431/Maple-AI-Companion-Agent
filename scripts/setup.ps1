# 一键安装:创建虚拟环境并安装依赖
$ErrorActionPreference = "Stop"

python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

Write-Host "Setup done. 激活环境: .\.venv\Scripts\Activate.ps1"
