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

## 3. 红线(任何阶段不可突破)

```text
SAFETY_MODE = MOCK_ONLY(当前)
无真实 Input / SendInput / Virtual HID
无 Automation
Recovery 不得绕过 Safety Gate
```
