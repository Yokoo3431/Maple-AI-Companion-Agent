# Kill Switch Contract(vNext)

## 三层

```text
GLOBAL_SOFTWARE     全局软件级
SESSION             会话级
USER_EMERGENCY      用户紧急停止(最高优先)
```

## 状态

```text
ARMED
ACTIVE
RELEASED
```

## 规则

```text
ANY ACTIVE KILL SWITCH → BLOCK ALL NEW ACTIONS + 终止活动 session
User Emergency Stop 优先级最高
```

本阶段禁止实现真实热键 hook;仅定义 contract 与 KillSwitchReference 模型。
