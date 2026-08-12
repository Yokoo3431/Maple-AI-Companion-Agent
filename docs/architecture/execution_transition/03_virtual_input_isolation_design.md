# Virtual Input Isolation Design(vNext)

> 目标:尽可能实现「第二套隔离输入通道」,让 Agent 操作绑定窗口,用户仍可正常办公。
> 本阶段只做设计比较,不决定具体实现,不虚构 Windows 不具备的能力。

## 1. 候选方向评估

### A. Foreground OS input simulation(SendInput / keybd_event 等)

| 维度 | 评估 |
| --- | --- |
| 影响用户物理键鼠 | 高(全局输入队列) |
| 需要 foreground focus | 是 |
| 移动用户鼠标 | 可能 |
| 抢占键盘 | 可能 |
| Windows 兼容性 | 高 |
| Maple 客户端兼容性 | 一般(依赖前台焦点) |
| 实现复杂度 | 低 |
| 安全风险 | 高(误发到错误窗口) |
| 可恢复性 | 低 |
| 调试难度 | 低 |
| 权限需求 | 低 |

### B. Window-targeted message / input 方式(PostMessage 等)

部分游戏客户端忽略 PostMessage 类输入或需特殊消息类型,兼容性不确定。

### C. Virtual HID / virtual device 方式

| 维度 | 评估 |
| --- | --- |
| 影响用户物理键鼠 | 低(独立虚拟设备) |
| 需要 foreground focus | 通常仍需目标窗口前台 |
| 移动用户鼠标 | 不移动用户鼠标(独立设备) |
| Windows 兼容性 | 中(需要签名驱动或内核支持,安装复杂) |
| Maple 客户端兼容性 | 需实测 |
| 实现复杂度 | 高 |
| 安全风险 | 中(驱动级权限) |
| 权限需求 | 高(驱动签名/管理员) |

### D. VM / isolated desktop / sandboxed game session

隔离性最好,但游戏性能/反作弊/账号绑定风险高,复杂度极高。

### E. Remote session / dedicated companion environment

隔离用户环境,但需额外会话管理与游戏兼容性验证。

## 2. Windows 限制(诚实声明)

Windows 默认输入模型以**全局输入队列 + 前台窗口**为中心,
目前不存在官方「第二套完全独立且不影响前台焦点」的通用输入通道。
因此「完全隔离」在纯 Win32 用户态**做不到保证**;只能通过
虚拟 HID / 独立会话等方案**尽量接近**,且必须逐项实测 Maple 客户端兼容性。

## 3. 推荐顺序(草案,待评审)

```text
1. Window-targeted 方案可行性验证(先契约 + 最小原型评审)
2. Virtual HID 方案(若客户端忽略 B,再评估驱动成本)
3. VM / isolated desktop(最后选项,隔离性最高但成本最高)
```

不把「直接 SendInput 前台模拟」作为首选。

## 4. 用户物理键鼠共存策略

| 项 | 设计 |
| --- | --- |
| preferred isolation | 虚拟 HID / 独立会话方向 |
| fallback strategy | 受限前台方案 + 强门控 |
| limitations | Windows 无官方完全隔离通道,必须实测 |
| focus requirements | 未来实现必须明确绑定窗口焦点策略 |
| cursor behavior | 禁止无授权移动用户鼠标;Agent 输入使用独立设备坐标 |
| keyboard conflict | 检测用户物理输入时 PAUSE / YIELD |
| emergency override | User Emergency Stop 最高优先 |
| user priority | **Human Input Priority > Agent Input** |

## 5. GameWindowBindingReference

```text
binding_id
process_reference
window_reference
title_reference
created_at
validation_status
```

绑定特定 process + 特定 window + 特定 session;禁止把「全局桌面输入」作为首选路径。
本阶段不调用任何 Win32 输入 API。
