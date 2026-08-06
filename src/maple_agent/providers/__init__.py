"""Provider 抽象层:Interface + Protocol + Mock(Phase 0,无真实调用)。"""

from maple_agent.providers.base import (
    BaseProvider,
    ErrorPayload,
    ProviderError,
    ProviderProtocol,
    ProviderStatus,
)
from maple_agent.providers.llm import (
    LLMProvider,
    LLMProviderProtocol,
    LLMRequest,
    LLMResult,
    MockLLMProvider,
)
from maple_agent.providers.ocr import (
    MockOCRProvider,
    OCRProvider,
    OCRProviderProtocol,
    OCRRequest,
    OCRResult,
)
from maple_agent.providers.storage import (
    MockStorageProvider,
    StorageProvider,
    StorageProviderProtocol,
)
from maple_agent.providers.vision import (
    MockVisionProvider,
    VisionProvider,
    VisionProviderProtocol,
    VisionResult,
)

__all__ = [
    "BaseProvider",
    "ErrorPayload",
    "LLMProvider",
    "LLMProviderProtocol",
    "LLMRequest",
    "LLMResult",
    "MockLLMProvider",
    "MockOCRProvider",
    "MockStorageProvider",
    "MockVisionProvider",
    "OCRProvider",
    "OCRProviderProtocol",
    "OCRRequest",
    "OCRResult",
    "ProviderError",
    "ProviderProtocol",
    "ProviderStatus",
    "StorageProvider",
    "StorageProviderProtocol",
    "VisionProvider",
    "VisionProviderProtocol",
    "VisionResult",
]
