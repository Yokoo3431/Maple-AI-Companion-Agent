# Migration Plan(vNext Proposal)

## 1. 阶段划分

```text
Phase M0  MOCK_ONLY(现状,生产默认)
Phase M1  Controlled Execution Contract 定型 + 门控实现(仍不接真实输入)
Phase M2  Real Vision Validation Gate(真实截图/OCR 验证通过前禁止进入长期执行)
Phase M3  Knowledge Quality Gate(地图/Portal/NPC/Quest/Monster 覆盖率达标)
Phase M4  CONTROLLED_TEST(显式启动 + 全套门控 + 最小受控原型)
Phase M5  HUMAN_SUPERVISED(session 级同意 + 边界权限 + 连续受控操作)
```

## 2. 硬性约束

- 默认保持 `MOCK_ONLY`;无配置不得进入 M4/M5;
- 每个阶段必须先评审再实现;
- M4 之前必须通过 Real Vision Validation Gate 与 Knowledge Quality Gate;
- 禁止跳过门控直接接 Input Provider。

## 3. Real Vision Validation Gate(当前结论)

当前 Vision Runtime 仍主要为 `MockScreenshotProvider` + Mock OCR
(Phase 11-A 只保留真实捕获 Provider 接口,未实现生产级真实截图/OCR 验证)。
因此:**当前真实感知能力不足以支持任何真实输入**,必须先完成真实视觉验证阶段。

## 4. Knowledge Quality Gate

进入受控执行前必须定义并达标:

```text
Map coverage
Portal coverage
NPC coverage
Quest coverage
Monster coverage
Source provenance
Game/server version
```

当前 demo 数据集(3 地图 / 2 连接 / 少量 NPC/Quest)仅为演示,**生产覆盖率仍需后续扩充**。
本阶段只定义 gate,不做大规模数据采集。

## 5. 依赖主线

```text
Action Verification(13-C)
↓ Recovery(13-B)
↓ Controlled Execution Architecture Review(13-D,本阶段)
↓ Future Safety Contract vNext
↓ Future Isolated Input Prototype
```
