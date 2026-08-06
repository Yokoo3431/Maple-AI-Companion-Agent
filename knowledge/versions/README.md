# versions/ 目录约定

每个子目录代表一个 **game_profile**(游戏档案),例如:

```text
versions/
├── classic_beta/     # 示例:经典怀旧档案(名称自定)
└── my_profile/
```

档案名通过 `.env` 中的 `MAPLE_KB_GAME_PROFILE` 指定,程序启动时检测
`knowledge/versions/<game_profile>/` 是否存在,不存在则提示导入。

> 该目录内容为运行时导入数据,默认不进 Git(见 .gitignore)。具体数据格式以
> `../schema/` 下的 JSON Schema 为准。
