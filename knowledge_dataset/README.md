# Phase 13-M 中国怀旧服知识快照

这是一个用于架构验证的有限、脱敏、版本化快照，不是完整生产数据库。

- 来源： [冒险岛怀旧服小册子](https://mxdc.dvg.cn/)
- 来源分类：`COMMUNITY_DATABASE`（社区整理，非官方腾讯/Nexon 数据源）
- Profile：`maple-cms-classic-community`
- Server profile：`cn-nostalgic-community`
- 快照版本：`2026-08-14`
- 规模：50 张地图、100 个 NPC、50 个任务、200 个道具
- hash：以 `manifest.json` 的 `content_hash` 为准

快照只保存 ID、中文名称、最小语义引用、canonical index 和 provenance。
不保存截图、图标/资源 URL、客户端文件、原始会话、日志、私有路径或个人数据。

任务引用可能指向本有限切片之外的实体；这会由校验报告中的
`missing_reference_count` 明确记录，不能据此推断全量覆盖或官方版本一致性。
