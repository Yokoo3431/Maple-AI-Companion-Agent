"""应用装配单测:启动流程产物。"""

from maple_agent.bootstrap import bootstrap
from maple_agent.events import EventBus
from maple_agent.game import MockGameWindowDetector
from maple_agent.runtime import RuntimeManager, RuntimeState


def test_bootstrap_assembles_app(tmp_path):
    result = bootstrap(logs_dir=tmp_path / "logs")
    assert isinstance(result.bus, EventBus)
    assert isinstance(result.runtime, RuntimeManager)
    assert result.runtime.state is RuntimeState.OFFLINE
    assert set(result.providers) == {"llm", "vision", "ocr", "storage"}
    assert all(provider.status.value == "INITIALIZED" for provider in result.providers.values())
    assert isinstance(result.detector, MockGameWindowDetector)
    assert result.app.title == "Maple AI Companion Agent"
    assert (tmp_path / "logs" / "startup.log").exists()
