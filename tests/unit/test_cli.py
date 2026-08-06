"""CLI 单测:参数解析 / doctor 自检 / test 命令。"""

from unittest import mock

from maple_agent.bootstrap import bootstrap
from maple_agent.cli import build_parser, main, prepare_for_start
from maple_agent.runtime import RuntimeState


def test_parser_commands():
    start_args = build_parser().parse_args(["start", "--port", "9090"])
    assert start_args.command == "start"
    assert start_args.port == 9090
    assert build_parser().parse_args(["doctor"]).command == "doctor"
    assert build_parser().parse_args(["test"]).command == "test"


def test_cli_doctor_ok(capsys):
    code = main(["doctor"])
    out = capsys.readouterr().out
    assert code == 0
    assert "[PASS]" in out
    assert "结果: 5/5 通过" in out


def test_cli_test_runs_pytest():
    with mock.patch("maple_agent.cli.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=0)
        code = main(["test"])
    assert code == 0
    run.assert_called_once()
    args = run.call_args.args[0]
    assert "-m" in args
    assert "pytest" in args


def test_prepare_for_start_sets_ready_not_running(tmp_path):
    result = bootstrap(logs_dir=tmp_path / "logs")
    prepare_for_start(result)
    assert result.runtime.state is RuntimeState.READY
