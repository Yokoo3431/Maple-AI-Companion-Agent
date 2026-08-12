# Execution Modes(vNext)

## MOCK_ONLY(当前生产默认)

- 无真实输入、无执行;
- 唯一允许的运行时模式。

## CONTROLLED_TEST(未来实验模式)

必须全部满足:

```text
显式启动
指定 game window
PermissionToken
Human Confirmation
Safety Gate ALLOW
action scope
timeout
rate limit
kill switch
replay
outcome verification
RealVisionReadiness = PASSED
KnowledgeQualityGate 达标
```

## HUMAN_SUPERVISED(未来连续受控操作)

仍需:

```text
session-level explicit consent
bounded permissions
emergency stop
window binding
safety escalation
```

## 禁止模式

```text
UNRESTRICTED
FULL_AUTO_NO_GUARD
```

本阶段二者不存在于 `ExecutionMode` 枚举,也不得在未来加入。
