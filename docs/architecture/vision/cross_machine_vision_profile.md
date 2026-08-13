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
  不复制 ROI 坐标;
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
