# Maple AI Companion Agent

《冒险岛怀旧服》AI Companion Agent —— 基于成熟 Agent 架构思想的桌面辅助程序。

> 免责声明:本项目仅供学习与技术研究使用。使用第三方辅助可能违反游戏运营规则,由此产生的账号风险由使用者自行承担。项目默认不包含任何真实键鼠自动化行为(Phase 0 仅基础架构)。

## 功能规划(分阶段)

> 项目目标保持不变:**Maple Companion AI(理解与规划)+ 未来隔离虚拟输入(仅规划,不实现真实输入)**。

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| Phase 0-7A | 基础架构 / 认知闭环(观察-决策-规划-确认-沙箱-反思-评估)/ 架构冻结 | ✅ 已完成 |
| Phase 7B-8F | 长期规划 / 环境理解 / 决策参考 / 人类对齐 | ✅ 已完成 |
| Phase 9A-9F | 记忆图谱 / 语义记忆 / Maple 上下文 / 领域知识 / 感知绑定 / 任务推理 | ✅ 已完成 |
| Phase 10A | Perception Fusion(多源感知融合,只读) | ✅ 已完成 |
| Phase 10B | L1 Reflex Foundation(HP/MP/UI 状态与危险事件快速感知,只读) | ✅ 已完成 |
| Phase 10C | Virtual Keyboard Isolation Layer(未来隔离虚拟输入层) | 规划中 |
| Phase 11A | Vision Runtime Foundation(窗口视觉读取 -> 结构化观察,只读) | ✅ 已完成 |
| Phase 11B | Game State Understanding(结构化 Maple 游戏状态,只读) | ✅ 已完成 |
| Phase 11C | World Knowledge Foundation(Maple 世界知识图谱,只读) | ✅ 已完成 |
| Phase 11D | Spatial World Model(地图内部空间认知,只读) | ✅ 已完成 |
| Phase 12A | Navigation Planning Foundation(只读导航规划参考) | ✅ 已完成 |
| Phase 12B | Behavior Planner Foundation(高层行为规划参考,只读) | ✅ 已完成 |
| Phase 12C | Action Proposal Foundation(动作建议参考,只读) | ✅ 已完成 |
| Phase 13A | Safety Gate Foundation(动作安全审核参考,只读) | ✅ 已完成 |
| Phase 13B | Failure Recovery Foundation(失败检测与恢复建议,只读) | ✅ 已完成 |
| Phase 13C | Action Outcome Verification(动作结果验证,只读) | ✅ 已完成 |
| Phase 13D | Controlled Execution Architecture Review(受控执行架构评审) | ✅ 已完成 |
| Phase 13E | Safety Contract vNext Formalization(安全契约 vNext 正式化) | ✅ 已完成 |
| Phase 13E.1 | Safety vNext Gate Enforcement Hardening(门执行加固) | ✅ 已完成 |

当前架构路线:

```text
Observation → Vision Evaluation → Knowledge → Decision → Planning
→ Human Confirmation → Permission Sandbox(MOCK_ONLY) → Reflection → Evaluation
→ Memory / Semantic Memory → Maple Context → Quest Reasoning → Perception Fusion
→ L1 Reflex(状态感知参考)
→ Vision Runtime(窗口视觉读取,结构化观察)
→ Game State Understanding(玩家/地图/实体/任务状态建模)
→ World Knowledge(外部知识 -> 地图图谱 -> 世界模型参考)
→ Spatial World Model(地图内部空间 / Portal / NPC / 任务区域)
→ Navigation Planning Reference(只规划,不执行)
→ Behavior Planning Reference(规划行为,不执行)
→ Action Proposal Reference(生成动作建议,不执行)
→ Safety Gate Reference(安全审核,不执行)
→ Action Outcome Verification(验证动作预期与实际状态变化,不执行动作)
→ Recovery Reference(检测失败并提出恢复建议,不执行)
→ Controlled Execution Architecture Review(仅评审,未启用真实输入)
→ Safety Contract vNext(仅契约,未启用)
→ Gate Enforcement Hardening(文档 Gate == 代码 Gate == 测试 Gate)
→ Real Vision Validation Gate
→ Knowledge Quality Gate
→ Future Controlled Execution Prerequisites
→ Future Isolated Input Prototype
```

保持:`READ_ONLY_FIRST / DATA_DRIVEN / MOCK_EXECUTOR_ONLY`,禁止真实键鼠控制与输入注入。

### Phase 11-C: World Knowledge Foundation

```text
External Game Knowledge
        ↓
Map Graph
        ↓
World Model Reference
```

当前阶段只建立世界理解(地图节点/连接/关联查询),为未来 Navigation Planner 提供只读基础。
**未实现**:Navigation、Input、Automation、路径跟随、移动控制。

### Phase 11-D: Spatial World Model

```text
World Knowledge
    ↓
Spatial World Model
    ↓
Future Navigation Planner
```

当前阶段只理解空间(Portal 位置 / NPC 位置 / Monster 区域 / Quest 目标区域 / 基础空间约束)。
**不执行导航**;所有空间输出仅为 Reference,不是移动命令。

### Phase 12-A: Navigation Planning

```text
Spatial World Model
    ↓
Navigation Planning Reference
    ↓
Future Behavior Planner
```

当前阶段只规划(BFS 路径搜索 / Portal 路由 / 成本估算 / 目标解析),输出仅 Navigation Reference。
**不执行移动**;禁止 Move / Execute 按钮与任何移动控制。

### Phase 12-B: Behavior Planning

```text
Navigation Planning
    ↓
Behavior Planning Reference
    ↓
Future Action Proposal
```

当前阶段规划高层行为(NAVIGATE / INTERACT / COMBAT / COLLECT / VERIFY 等语义步骤),
输出仅 Behavior Reference。**不执行**;COMBAT_REFERENCE 不是 Attack Command,
禁止 Execute / Run 按钮与任何真实输入。

### Phase 12-C: Action Proposal

```text
Behavior Planning
    ↓
Action Proposal Reference
    ↓
Future Safety Gate
    ↓
Future Input Layer
```

当前阶段把行为步骤转换为语义动作建议(OBSERVE / NAVIGATE / INTERACT / COMBAT / COLLECT / VERIFY / WAIT),
输出仅 Action Proposal Reference。**不执行**;禁止 Execute / Run / Send 按钮与任何真实输入。

### Phase 13-A: Safety Gate

```text
Action Proposal
    ↓
Safety Gate
    ↓
Future Input Isolation
```

当前阶段对动作建议执行确定性安全审核(HP 风险 / 死亡风险 / 未知目标 / 非法动作),
输出仅 SafetyEvaluationReference(ALLOW_REFERENCE / WARNING_REFERENCE / BLOCKED_REFERENCE)。
**不执行**;审核结果不是执行许可,禁止 Approve Execute / Run / Send。

### Phase 13-B: Failure Recovery

```text
Action Proposal
    ↓
Safety Gate
    ↓
Recovery Foundation
    ↓
Future Input Isolation
```

当前阶段检测动作失败(导航超时 / 状态不匹配 / 战斗失败 / 安全阻止)并提出恢复建议
(RETRY / WAIT_OBSERVATION / REPLAN / CHANGE_TARGET / ABORT)。
输出仅 RecoveryReference。**不执行恢复**;禁止 Execute / Retry Now / Run 按钮与任何真实输入。

### Phase 13-C: Action Outcome Verification

```text
Action Proposal
→ Safety Gate
→ Action Outcome Verification
→ Failure Recovery
→ Future Virtual Input Isolation
```

当前阶段验证动作预期与实际状态变化(Before/After GameState 比较 + 结构化证据 +
SUCCESS / PARTIAL_SUCCESS / FAILED / TIMEOUT / INCONCLUSIVE / BLOCKED 判定)。
**不执行动作**;HP 下降仅作为战斗证据,不单独判定失败;所有输出仅为 Reference。

### Phase 13-D: Controlled Execution Architecture Review

```text
Action Verification
↓ Recovery
↓ Controlled Execution Architecture Review
↓ Future Safety Contract vNext
↓ Future Isolated Input Prototype
```

本阶段仅产出受控执行架构评审文档
(`docs/architecture/execution_transition/`,含 Contract Draft / Threat Model / Migration Plan / ADR-001)。
**Phase 13-D does not enable live input.** `SAFETY_MODE` 仍为 `MOCK_ONLY`,
无真实 Input / SendInput / Virtual HID / Automation;只有未来 Architecture Review
批准 Safety Contract vNext 后才允许受控原型。

### Phase 13-E: Safety Contract vNext Formalization

```text
Controlled Execution Architecture Review
↓ Safety Contract vNext(仅契约)
↓ Real Vision Validation Gate
↓ Knowledge Quality Gate
↓ Future Controlled Execution Prerequisites
↓ Future Isolated Input Prototype
```

**Safety vNext is contract only.** Runtime remains `MOCK_ONLY`.
No real input is enabled.ADR-001 已批准**架构方向**,但不授权任何真实输入;
Real Vision 当前 `NOT_READY`、Knowledge 当前 `FOUNDATION_ONLY`,
整体 Controlled Execution readiness 当前 `NOT_READY`。

### Phase 13-E.1: Safety vNext Gate Enforcement Hardening

```text
13-E Safety Contract vNext
↓ 13-E.1 Gate Enforcement Hardening
↓ 13-F Real Vision Validation
↓ 13-G Knowledge Quality Gate
↓ Future Controlled Execution Prerequisites
```

Safety vNext 文档 Gate 与 machine-readable Gate 已完全对齐
(强类型 `GateInputReference` + 10 级 gate + `GateCheckReference` 审计 + 预算/过期/杀开关全量 enforce)。
仍不启用真实输入;Overall Controlled Execution Readiness 仍为 `NOT_READY`。

## 快速开始(Phase 0)

需要 Python 3.11+。

**第一次使用(换电脑 / 新环境,一键恢复):**

```powershell
git clone <repo-url> Maple-Agent
cd Maple-Agent
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

setup.ps1 会自动完成:检查 Python ≥ 3.11 → 创建/复用 .venv → 安装依赖 → 创建 logs/ sessions/ knowledge/ config/ 目录 → 从 .env.example 生成 .env → 运行 doctor 自检。然后双击 `launcher\Maple Agent 启动.bat` 即可启动。

**日常使用:**直接双击 `launcher\Maple Agent 启动.bat`。

**开发模式(可选):**

```powershell
python -m pytest                          # 运行测试
python -m maple_agent doctor              # 环境自检
python -m maple_agent start               # 启动 WebUI 控制台(http://127.0.0.1:8080)
python -m maple_agent test                # 运行测试套件
```

Phase 0 Release 说明见 [docs/06-phase0-release.md](docs/06-phase0-release.md)。

## 普通用户启动方式(Windows,无需命令行)

1. 双击 `launcher\Maple Agent 启动.bat`;
2. 启动器自动检查 Python 与项目 venv,缺失时弹出中文提示;
3. 服务就绪后自动打开浏览器 http://127.0.0.1:8080(默认 READY 状态,不会自动进入 RUNNING);
4. 启动记录保存在 `launcher\launcher.log`。

排查启动问题:双击 `launcher\Maple Agent 启动 Debug.bat`,窗口会保持打开(显示完整检查过程),便于查看错误。

## 外部审核包生成流程(External Review Package)

用于把当前项目打包,提交给其他 AI 模型做架构审核、安全审核与代码质量审核。

```powershell
# 方式一:命令行(在项目根目录执行)
powershell -ExecutionPolicy Bypass -File scripts\create_review_package.ps1

# 方式二:右键 scripts\create_review_package.ps1 -> 使用 PowerShell 运行
```

生成结果:

- `review_package/`:README_REVIEW.md、PROJECT_STATUS.md、ARCHITECTURE_SUMMARY.md、CHANGELOG.md、docs/、src/、tests/、requirements.txt、pyproject.toml;
- `Maple_AI_Companion_Agent_review_v0.1.0.zip`:可直接上传给外部 AI 审核。

排除内容(脚本自动校验,不进入包内):

- .venv、__pycache__、*.pyc、logs/、launcher.log、.env、review_package 自身、本地绝对路径;
- API Key 与用户配置不在包内(它们只存在于本机 .env)。

注意事项:每次运行会重新生成并覆盖 `review_package/` 与 zip;`PROJECT_STATUS.md` 会自动写入实测 pytest 数量。

## 架构

四层结构 + 横切基础设施:

```text
交付层:Web UI(FastAPI + Jinja2 + WebSocket)、Runtime Manager
核心层:Agent Controller、L1 Reflex、L2 Planner(LLM Provider)、Memory
适配层:Vision(截图/OpenCV/OCR Provider)、Input(Interface → Provider)、Game Window(只读)
数据层:Knowledge Base(versions/game_profile)、SQLite、Sessions/Replay、Logs
横切:Config、Logging、Event Bus(Reflex / Runtime / Error 事件)
```

详细设计见 [docs/README.md](docs/README.md)。

## 开发约定

- 每次提交附:修改文件列表 / Commit 建议 / 测试结果 / 运行日志 / 错误日志 / 下一步建议;
- 核心层只依赖抽象接口(Input / Vision / LLM Provider),禁止反向依赖;
- 禁止硬编码;API Key 与本地隐私只放 `.env`(不进 Git);
- Phase 0 禁止:自动移动/攻击/任务/购买、真实键鼠控制、内存读取。

## License

MIT
