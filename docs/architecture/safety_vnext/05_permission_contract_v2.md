# Permission Contract v2

## 1. Token ≠ Executor(正式语义)

```text
PermissionToken:
  永远不执行动作
  永远不包含 raw keyboard / mouse input
  永远不是 Executor
  永远不是 Action Command

Future Controlled Executor:
  必须验证 PermissionToken
  只能把 token 当作 execution prerequisite credential

Token != Executor
Token != Input
Executor requires valid Token
```

## 2. PermissionScopeV2

```text
OBSERVE
NAVIGATE
INTERACT
COMBAT
COLLECT
USE_ITEM
```

复用 Phase 6-C Confirmation 系统,不重建第二套。

## 3. PermissionPolicyV2

```text
scope
target_restrictions
window_restriction
expires_at
max_actions
max_rate
allowed_action_types
session_restriction
```

禁止 `ALL_ACCESS` 作为默认值;过期/撤销/窗口变更即失效。
