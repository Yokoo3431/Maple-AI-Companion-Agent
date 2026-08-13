# Cross-Machine Vision Profile(Phase 13-I.2)

> 目标:同一套 Perception Pipeline 在 HOME / OFFICE / Future PC 泛化,
> 避免无限设备硬编码(`home_pc_xxx / office_pc_xxx / computer3_xxx ...`)。

## 1. 架构

```text
Base Profile(maple_classic_default,归一化布局)
↓ Resolution / DPI Transform(VisionProfileTransformer)
↓ Machine Profile(resolution / window_mode / 少量 calibration overlay)
↓ 同一套 HpMpGeometryExtractor / TemplateLibrary / VisionScheduler
```

## 2. Normalized ROI

`NormalizedROI(x/y/width/height ∈ 0..1)` 相对 client width/height:

```text
pixel_x = normalized_x * client_width * dpi_scale(round)
pixel_y = normalized_y * client_height * dpi_scale(round)
```

ROI 一律基于 **client-local 坐标**,与 desktop absolute(含副屏负坐标)无关。

## 3. Profile 继承

- `maple_classic_default.json`:归一化布局(由 HOME 2560×1440 推导);
- `home_pc_2560x1440.json`:旧 pixel 格式,由 registry 自动迁移(向后兼容);
- `office_pc_1920x1080.json`:仅保存 resolution/window_mode/base_profile 引用,
  不复制 ROI 坐标。注意:**resolution = GAME CLIENT(1366×768,transform 目标)**,
  `display_resolution = 1920×1080`(显示器,仅元数据);不得把显示器分辨率当作
  客户端分辨率用于 ROI transform;
- 未来机器:新增 resolution + 少量 calibration deltas 即可。

## 4. DPI

transform 携带 `dpi_scale` 元数据(HOME/OFFICE 当前均为 1.0);
未来 125% / 150% scaling 只经 transform 扩展,不破坏 ROI 语义。

## 5. 双显示器 / Window Binding

- client-local ROI 与窗口在哪个显示器无关;
- 副屏负坐标(left<0)不影响 ROI;
- WGC 使用窗口 HWND 绑定,不依赖桌面坐标;
- ImageGrab bbox 用 ClientToScreen 屏幕坐标(可负)。

## 6. 跨机对比(CROSS_MACHINE)

`CrossMachineVisionBenchmark` 对比 HOME(sanitized 13-I.1)与 OFFICE:

```text
resolution / dpi / capture provider / hp_error / mp_error
map top1 / template margin / capture/geometry/template/ocr latency
profile transform status
```

每项输出 `PASS / DEGRADED / FAIL / N/A`,不制造魔法总分。

## 7. Phase 13-I.3 实测(Home PC,2026-08-13)

### Client vs Display 分辨率(语义修正)

- OFFICE:display=1920×1080,GAME CLIENT≈1366×768(windowed);
  `office_pc_1920x1080.json` 已修正 `resolution=1366x768`(transform 目标)+
  `display_resolution=1920x1080`(仅元数据)。
- HOME:display=2560×1440,GAME CLIENT=2560×1440(fullscreen-windowed);
  窗口切换为 windowed 时实测 WGC 帧 1922×1112(client≈1920×1080),
  ROI 按**实际帧尺寸**归一化换算(collector 已支持)。

### 实测结果(HOME=REAL_HOME / OFFICE=REAL_OFFICE pause evidence)

| 项 | HOME | OFFICE | 判定 |
| --- | --- | --- | --- |
| Profile transform | 2560×1440 + 1922×1112 实测 OK | 1366×768 transform OK(单测) | PASS |
| WGC | fg 166ms / bv 388ms / occ 392ms / min NOT_SUPPORTED | fg 405ms / min 25 帧 WINDOW_INVALID | PASS |
| HP geometry | 绿色分段条,读 0.128 vs GT 1.0(误差 0.87) | N/A(无真实数据集) | FAIL |
| MP geometry | 读 0.074 vs GT 1.0(误差 0.93) | N/A | FAIL |
| Map 判别 | 2 图(射手村/集市)28 查询 top1=1.0,unknown=0,FP=0,margin 0.86 | N/A | PASS |
| OCR | ROI 719ms,准确率 0.0 | Tesseract 二进制不可用 | FAIL(DEGRADED) |
| Event scheduler | idle 7 帧跳过 OCR,变化触发 template+OCR | - | PASS |

### 关键 blocker

该 Unity 客户端的 HP/MP 条为**绿色分段条**;当前 median-row-extent 模型只能
测到单个段长(约 5-13%),不能代表填充率。需 13-I.4 分段条模型校准
(段数/点亮段计数),禁止 post-hoc 常量补偿。
