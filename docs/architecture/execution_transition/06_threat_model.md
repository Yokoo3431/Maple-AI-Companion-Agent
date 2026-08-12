# Threat Model(vNext)

| 威胁 | 描述 | Mitigation |
| --- | --- | --- |
| Wrong Window | 动作发送到错误窗口 | Window Binding 校验(binding_id + process + window + session 四重匹配) |
| Focus Drift | 游戏不再是目标窗口 | 每次 EXECUTING 前重校验 focus/binding;漂移即 PAUSE/BLOCK |
| Stuck Key | key down 未收到 key up | 输入适配器要求成对事件 + 超时补偿 + 会话终止时强制清理 |
| Runaway Agent | 持续动作无法停止 | Kill Switch 三层 + max_continuous_execution_time + rate limit |
| Recovery Loop | Retry 无限循环 | max_retry_count / max_failure_count,超限转 ABORT + 人工介入 |
| False Vision | 错误识别地图/NPC/HP | Real Vision Validation Gate + outcome verification + 低置信不执行 |
| Stale Permission | 过期 token 被复用 | expires_at 校验 + session 绑定 + 窗口变更即失效 |
| Session Hijack | 旧 binding 被其他窗口复用 | binding 唯一化 + validation_status 每次执行前校验 |
| User Interaction Collision | 用户同时操作键鼠冲突 | 用户输入检测 → PAUSE/YIELD(Human Input Priority) |
| Game Client Update | 客户端更新改变定位/UI/输入行为 | 版本绑定 + 知识数据 gate + 客户端更新后重新验证 |

原则:任何威胁触发一律 BLOCK / PAUSE,禁止绕过门控继续执行。
