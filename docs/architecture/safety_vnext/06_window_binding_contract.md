# Window Binding Contract(vNext)

## GameWindowBindingReference

```text
binding_id
process_reference
window_reference
title_reference
session_reference
created_at
expires_at
validation_status
```

## 约束

- 绑定特定 process + 特定 window + 特定 session;
- 禁止以「全局桌面输入」作为首选路径;
- `validation_status` 必须为 PASSED 才可通过 gate;
- session 的 `window_binding_id` 必须与 binding 一致,否则 Wrong Window → BLOCKED;
- 本阶段不调用任何 Win32 Input API。
