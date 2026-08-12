# Acceptance Gate(vNext)

## 1. 进入 CONTROLLED_TEST 的验收条件

- [ ] Controlled Execution Contract 经架构评审批准
- [ ] Safety Architecture vNext 批准并版本化(仍默认 MOCK_ONLY)
- [ ] Real Vision Validation Gate 通过(真实截图 + OCR 验证)
- [ ] Knowledge Quality Gate 达标
- [ ] Permission/Confirmation v2 实现并测试
- [ ] Window Binding + Execution Session 实现并测试
- [ ] Kill Switch 三层实现并测试
- [ ] Rate Limit / Action Budget 实现并测试
- [ ] Outcome Verification 强制接入执行循环
- [ ] Threat Model mitigation 全部落地
- [ ] 全量 pytest + ruff + architecture contract 通过
- [ ] 显式启动配置(禁止默认开启)

## 2. 进入 HUMAN_SUPERVISED 的验收条件

- CONTROLLED_TEST 长期稳定运行记录
- session-level explicit consent 实现
- bounded permissions + emergency stop 实测
- 用户输入冲突 PAUSE/YIELD 实测
- 长时间运行审计/回放完备

## 3. Current v1 Restrictions(当前 main)

```text
MOCK_ONLY
NO REAL INPUT
NO AUTOMATION
NO VIRTUAL HID
NO SENDINPUT
Recovery 不得绕过 Safety Gate
```

这是 Phase 7-A / Safety v1 / 当前 main 的绝对约束。

## 4. Permanent Safety Invariants(未来跨版本永久)

```text
NO UNAUTHORIZED EXECUTION
NO SAFETY BYPASS
NO PERMISSION BYPASS
NO WRONG WINDOW
NO UNBOUNDED EXECUTION
NO RECOVERY DIRECT EXECUTION
NO LIVE DEFAULT
NO UNRESTRICTED MODE
```

当前限制与永久不变量是不同概念:
CONTROLLED_TEST 未来可在批准后合法存在,但永久不变量在任何版本都不可突破。

## 5. CONTROLLED_TEST Entry Gates

```text
Safety vNext
Real Vision
Knowledge Quality
Permission v2
Window Binding
Session
Kill Switch
Rate Limit
Outcome Verification
Threat Mitigation
Explicit Enable
```

任何一项未满足一律 `BLOCKED`,禁止 fallback 绕过。
