# Extension Guideline

> Phase 7-A Architecture Freeze(冻结版本: 1.0)

## 新增模块必须满足

1. **独立目录**: 新能力放在独立 `src/maple_agent/<module>/` 目录
2. **明确输入输出**: 输入输出必须为强类型 Pydantic 模型
3. **不可修改旧模块行为**: 禁止重构/改动 Phase 0-6E 核心逻辑
4. **必须拥有 Replay**: 每个新模块必须产出可审计 Trace
5. **必须拥有 Unit Test**: pytest 用例覆盖核心路径
6. **必须通过 Safety Review**: 不突破 `safety_boundary.md` 约束

## 依赖规则

- 遵循单向分层(见 `architecture_overview.md`)
- 禁止循环依赖
- 禁止反向依赖 `agent_loop`(顶层编排)
- 新模块如被已有模块消费,只能通过注入/接口,不修改旧模块源码

## 数据兼容

- 新字段必须带默认值
- 禁止删除既有字段
- 语义变化必须升 `schema_version`
- 旧 Trace 必须可读

## 安全审查清单

新增/修改代码前检查:

- [ ] 无 SendInput / pyautogui / keyboard / mouse / click
- [ ] 无 Hook / DLL / 内存读取 / 客户端修改
- [ ] 无自动控制 / 自动任务
- [ ] 执行路径仅 MOCK_ONLY
- [ ] 所有动作经过确认门控 + 权限令牌
- [ ] 有 Replay 与 Unit Test

## 建议的扩展方式

- 真实窗口观察验证(仅读取,复用 WindowsCaptureProvider)
- 人工审核关卡(Human Confirmation 扩展)
- 更多知识数据集(Data Driven 导入)
- 评估指标扩充(Evaluation Benchmark 扩展)

真实输入层仍属于**未授权方向**,任何此类开发需先经架构评审。
