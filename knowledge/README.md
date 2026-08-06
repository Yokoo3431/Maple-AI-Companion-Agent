# 知识库说明

本目录为外部知识库框架(Phase 0 仅建立 schema,不导入具体游戏数据)。

## 目录约定

```text
knowledge/
├── schema/                    # JSON Schema(入库)
│   ├── maps.schema.json
│   ├── npc.schema.json
│   ├── monster.schema.json
│   ├── items.schema.json
│   ├── quests.schema.json
│   └── routes.schema.json
└── versions/                  # game_profile 目录(运行时导入,不入库)
    └── <game_profile>/        # 名称由配置 MAPLE_KB_GAME_PROFILE 指定
        ├── maps.json
        ├── npc.json
        ├── monster.json
        ├── items.json
        ├── quests.json
        └── routes.json
```

## 约定

- 不绑定固定版本号(如 v113);档案名由 `MAPLE_KB_GAME_PROFILE` 配置;
- 数据来源:用户整理、社区公开资料、人工录制、JSON/CSV 导入;
- 启动时检测档案是否匹配,不匹配则提示更新;
- 支持手动导入与增量更新,生成 `knowledge_update_report.md`。
