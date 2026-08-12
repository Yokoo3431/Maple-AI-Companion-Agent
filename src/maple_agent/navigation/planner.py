"""NavigationPlanner:只读导航规划(BFS + 确定性规则,无 LLM)。"""

from __future__ import annotations

from maple_agent.game_state.models import GameStateReference
from maple_agent.logging_setup import new_id
from maple_agent.navigation.cost import CostCalculator
from maple_agent.navigation.models import (
    NavigationReference,
    RouteStep,
    RouteStepType,
)
from maple_agent.navigation.resolver import TargetResolver
from maple_agent.navigation.route_graph import RouteGraph
from maple_agent.quest_reasoning.models import QuestGoalReference
from maple_agent.spatial_world.models import SpatialWorldReference
from maple_agent.world_knowledge.models import WorldKnowledgeReference


class NavigationPlanner:
    """把当前状态 + 目标解析为导航参考(不执行)。"""

    def __init__(
        self,
        *,
        route_graph: RouteGraph | None = None,
        cost_calculator: CostCalculator | None = None,
        target_resolver: TargetResolver | None = None,
    ) -> None:
        self.route_graph = route_graph or RouteGraph()
        self.cost_calculator = cost_calculator or CostCalculator()
        self.target_resolver = target_resolver or TargetResolver()
        self.last_reference: NavigationReference | None = None

    def plan(
        self,
        *,
        target: str,
        game_state_reference: GameStateReference | None = None,
        spatial_world_reference: SpatialWorldReference | None = None,
        world_knowledge_reference: WorldKnowledgeReference | None = None,
        quest_goal_reference: QuestGoalReference | None = None,
    ) -> NavigationReference:
        current_map = ""
        if (
            game_state_reference is not None
            and game_state_reference.current_map is not None
        ):
            current_map = game_state_reference.current_map.map_name
        elif (
            world_knowledge_reference is not None
            and world_knowledge_reference.current_map
        ):
            current_map = world_knowledge_reference.current_map
        target_info = self.target_resolver.resolve(
            target,
            spatial=spatial_world_reference,
            world_knowledge=world_knowledge_reference,
        )
        steps: list[RouteStep] = []
        confidence = 0.3
        reasoning: list[str] = []
        if target_info["kind"] in ("NPC", "QUEST_TARGET"):
            step_type = (
                RouteStepType.LOCAL_MOVE_REFERENCE
                if target_info["kind"] == "NPC"
                else RouteStepType.QUEST_TARGET_REFERENCE
            )
            steps.append(
                RouteStep(
                    step_type=step_type,
                    source=current_map,
                    target=target,
                    metadata=target_info["location"],
                )
            )
            confidence = 0.9
            reasoning.append(
                f"{target_info['kind']} {target} 位于当前地图"
            )
        elif target_info["kind"] == "MAP":
            if (
                world_knowledge_reference is not None
                and world_knowledge_reference.map_connections
            ):
                self.route_graph = RouteGraph.build_from_connections(
                    world_knowledge_reference.map_connections
                )
            path = self.route_graph.find_path(current_map, target)
            if len(path) >= 2:
                steps = [
                    RouteStep(
                        step_type=RouteStepType.PORTAL_REFERENCE,
                        source=path[index],
                        target=path[index + 1],
                        metadata={},
                    )
                    for index in range(len(path) - 1)
                ]
                confidence = 0.85
                reasoning.append(
                    "跨地图路径: " + " → ".join(path)
                )
            elif len(path) == 1:
                steps.append(
                    RouteStep(
                        step_type=RouteStepType.LOCAL_MOVE_REFERENCE,
                        source=current_map,
                        target=target,
                        metadata={},
                    )
                )
                confidence = 0.85
            else:
                reasoning.append(f"未找到到 {target} 的路径")
        else:
            reasoning.append(f"目标 {target} 无法解析")
        cost = self.cost_calculator.calculate(steps)
        reasoning.append(f"估算成本: {cost}")
        reference = NavigationReference(
            navigation_id=new_id(),
            start_location=current_map,
            target_location=target,
            route_steps=steps,
            estimated_cost=cost,
            confidence=round(min(1.0, max(0.0, confidence)), 4),
            reasoning=reasoning,
            validation="",
        )
        self.last_reference = reference
        return reference
