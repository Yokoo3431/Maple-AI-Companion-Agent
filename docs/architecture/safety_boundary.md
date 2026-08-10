# Safety Boundary

> Phase 7-A Architecture Freeze(永久安全规则,冻结版本: 1.0)

## 允许

- Observation(屏幕观察/截图/图像元数据)
- Analysis(分析/评估/反思)
- Planning(计划/决策建模)
- Confirmation(人工确认)
- Mock Execution(受限沙箱,MOCK_ONLY)
- Replay(审计回放)

## 禁止(永久)

- Physical Input(SendInput / pyautogui / keyboard / mouse / click / Win32 输入注入)
- Automation Control(自动控制 / 自动任务 / 自动战斗)
- Client Modification(客户端修改 / 注入 / Hook / DLL)
- Memory Reading(游戏进程内存读取)
- 任何真实游戏操作

## 模式约束

- 执行器统一 `MOCK ONLY`,禁止真实执行器接入
- 所有动作必须经过 Human Confirmation 门控
- 沙箱必须验证 PermissionToken(存在/批准/未过期/scope 匹配/策略允许)
- PermissionToken 仅为逻辑许可,禁止绑定真实执行

## 设计原则

1. **Read Only First**: 任何能力先以只读方式落地
2. **Data Driven**: 行为由结构化数据驱动
3. **Contract First**: 先定义契约,再实现
4. **Safety First**: 安全边界不可协商

## 安全标记(供测试校验)

```python
SAFETY_MODE = "MOCK_ONLY"
SAFETY_BOUNDARY = {
    "allowed": ["observation", "analysis", "planning",
                "confirmation", "mock_execution", "replay"],
    "forbidden": ["physical_input", "automation_control",
                  "client_modification"],
}
```

任何阶段开发不得突破以上边界;违反即视为安全回归。
