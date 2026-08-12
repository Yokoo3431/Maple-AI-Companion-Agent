# Permission & Confirmation v2(vNext Proposal)

## 1. 现有语义(Phase 6-C,复用)

```text
ConfirmationRequest: confirmation_id / action / target / risk_level / vision_score / confidence / status
ConfirmationStatus: PENDING / APPROVED / REJECTED / EXPIRED / BLOCKED
PermissionToken: token_id / confirmation_id / approved / scope / expires_at
```

不重建第二套系统,只在既有契约上做**兼容扩展**(新字段带默认值)。

## 2. PermissionScope v2

至少支持:

```text
OBSERVE
NAVIGATE
INTERACT
COMBAT
COLLECT
USE_ITEM
```

## 3. PermissionToken v2 扩展字段(草案)

```text
scope(从字符串升级为结构化 PermissionScope)
target_restriction     允许的目标白名单
window_restriction     绑定的窗口
duration               有效期
max_actions            动作预算
max_rate               速率上限
allowed_action_types   允许的动作类型
```

## 4. 硬性约束

- 禁止 `ALL_ACCESS` 作为默认值;
- token 必须关联 `confirmation_id`,APPROVED 才有效;
- 过期 / 撤销 / 窗口变更后 token 必须失效(防 Stale Permission);
- token 仅为逻辑许可,永不绑定真实执行。

## 5. Human Confirmation v2 语义

```text
session-level explicit consent(仅 HUMAN_SUPERVISED)
bounded permissions(每次 session 限定范围)
emergency stop(随时可终止)
window binding 校验
safety escalation(风险升高自动要求重新确认)
```
