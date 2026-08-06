"""setup.ps1 集成测试(仅 Windows,验证环境恢复脚本)。"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SETUP_SCRIPT = REPO_ROOT / "scripts" / "setup.ps1"

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="setup.ps1 仅 Windows")


def _run_setup(*args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SETUP_SCRIPT),
            *args,
        ],
        capture_output=True,
        timeout=180,
    )
    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")
    return proc.returncode, stdout, stderr


def test_setup_check_only_on_real_project():
    """Python 检测、venv 检测、依赖检测、doctor 自检。"""
    code, stdout, stderr = _run_setup("-CheckOnly")
    assert code == 0, stdout + stderr
    assert "[setup]" in stdout
    assert "doctor" in stdout.lower()


def test_setup_creates_venv_in_temp(tmp_path: Path):
    """venv 创建逻辑。"""
    code, stdout, stderr = _run_setup(
        "-ProjectRoot",
        str(tmp_path),
        "-VenvDir",
        str(tmp_path / ".venv"),
        "-VenvOnly",
    )
    assert code == 0, stdout + stderr
    assert (tmp_path / ".venv" / "Scripts" / "python.exe").exists()
