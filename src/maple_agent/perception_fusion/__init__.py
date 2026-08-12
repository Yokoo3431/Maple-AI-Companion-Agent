"""Perception Fusion 层(Phase 10-A,多源感知融合参考,只读)。"""

from maple_agent.perception_fusion.conflict import ConflictDetector
from maple_agent.perception_fusion.consistency import ConsistencyScorer
from maple_agent.perception_fusion.fusion import (
    PerceptionFusionEngine,
    save_perception_fusion_trace,
)
from maple_agent.perception_fusion.models import (
    FusionSourceInput,
    PerceptionFusionReference,
)
from maple_agent.perception_fusion.validator import (
    PerceptionFusionValidationResult,
    PerceptionFusionValidator,
    PerceptionFusionVerdict,
)

__all__ = [
    "ConflictDetector",
    "ConsistencyScorer",
    "FusionSourceInput",
    "PerceptionFusionEngine",
    "PerceptionFusionReference",
    "PerceptionFusionValidationResult",
    "PerceptionFusionValidator",
    "PerceptionFusionVerdict",
    "save_perception_fusion_trace",
]
