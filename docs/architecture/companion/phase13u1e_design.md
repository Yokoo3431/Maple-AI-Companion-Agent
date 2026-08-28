# Phase 13-U.1e — Minimal Real Semantic Evidence Closure

## Boundary

本阶段只修复既有 Real Vision Result 到 `CurrentObservation` 的最薄契约桥接，不新增 Vision pipeline、OCR engine、detector family、Knowledge inference、Resolver、Planner 或 Executor。安全边界保持 `SAFETY_MODE=MOCK_ONLY`、READ ONLY、NO INPUT、NO EXECUTION、NO AUTOMATION。

## Confirmed audit

Phase 13-U.1d 的真实短诊断已证明 Capture、OCR 调用、Snapshot 和 Temporal history 可以运行，但 `VisionDetector`/`GameStateParser` 没有产生可用结构化 candidate。静态审计还确认：`GameStateParser` 的既有 `ScreenObservation` 没有一个进入正式 Companion Runtime 的 adapter 入口；`ExistingVisionObservationAdapter` 原先只接受已经构造好的 `PerceptionEvidence`。

## Minimal bridge

`ExistingVisionObservationAdapter.from_screen_observation()` 只复制 `ScreenObservation` 已存在的字段：

- `visible_map` → `map` evidence；
- `visible_entities` → `entity` evidence；
- `quest_reference` → `quest` evidence；
- `hp_reference` / `mp_reference` → 既有 `PlayerStateReference`。

每条证据保留 `frame_id`、timestamp、source、parser method 和原 observation confidence。没有 canonical enrichment、别名推断或默认实体。HP/MP 不伪装成 KnowledgeEntity。

## Runtime path

```text
Existing Vision Result
  → VisionDetector / GameStateParser
  → ScreenObservation
  → ExistingVisionObservationAdapter.from_screen_observation
  → CurrentObservation
  → existing EvidenceResolver / StateReducer
  → SemanticGameState / CompanionSnapshot
```

这仍然使用唯一的既有 Resolver、Temporal Memory、Knowledge Graph 和 Companion Runtime。

## Real validation status

代码桥接后已在用户手动保持客户端可见时完成 `93.39` 秒真实诊断：27/27 capture 成功、27/27 snapshot 成功、异常 0，但 Map candidate、HP/MP candidate 和 PerceptionEvidence 仍为 0。因此真实结论保持 `REAL_SEMANTIC_EVIDENCE=NOT_CLOSED`，不能把 Adapter 的确定性单测当作真实视觉闭环。

## Known limitations

- 仓库没有可复用的合法 map template manifest/assets，当前存在 `MAP_TEMPLATE_ASSET_GAP`；
- 当前实时 OCR 输出不满足已有 prefix/value parser 契约；
- 本适配器不会把不可见、未解析或知识库候选变成观察事实；
- Real Vision、Knowledge 和 Overall readiness 不因 adapter 存在而自动提升。
