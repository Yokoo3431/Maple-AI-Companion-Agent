"""Provider 抽象层:Interface + Protocol + Mock + 真实适配器(OCR 等)。"""

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
    OCRBBox,
    OCRProvider,
    OCRProviderProtocol,
    OCRRequest,
    OCRResult,
    TesseractOCRProvider,
    WindowsOCRProvider,
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
    "OCRBBox",
    "OCRRequest",
    "OCRResult",
    "TesseractOCRProvider",
    "WindowsOCRProvider",
    "ProviderError",
    "ProviderProtocol",
    "ProviderStatus",
    "StorageProvider",
    "StorageProviderProtocol",
    "VisionProvider",
    "VisionProviderProtocol",
    "VisionResult",
]
