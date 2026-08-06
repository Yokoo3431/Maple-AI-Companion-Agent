# Maple AI Companion Agent — Windows 部署指南(Phase 0)

## 1. Windows 部署流程

### 第一次使用(换电脑 / 新环境)

1. 安装 Python 3.11+:
   - 下载地址:https://www.python.org/downloads/
   - 安装时勾选 **Add python.exe to PATH**;
2. 获取项目代码:

   ```powershell
   git clone https://github.com/Yokoo3431/Maple-AI-Companion-Agent.git Maple-Agent
   cd Maple-Agent
   ```

   (没有 git 经验时,可在 GitHub 页面 Code → Download ZIP,解压后进入目录)
3. 一键恢复环境:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
   ```

   setup.ps1 自动完成:Python ≥ 3.11 检查 → .venv 创建/复用 → 依赖安装 → 创建 logs/ sessions/ knowledge/ config/ → 从 .env.example 生成 .env → 运行 doctor 自检;
4. 双击 `launcher\Maple Agent 启动.bat` 启动,浏览器自动打开 http://127.0.0.1:8080。

### 日常使用

- 直接双击 `launcher\Maple Agent 启动.bat`;
- 停止:在 WebUI 点击 STOP,或关闭 maple_agent 进程。

### 更新代码

```powershell
git pull
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

## 2. Launcher 使用方法

| 入口 | 说明 |
| --- | --- |
| `Maple Agent 启动.bat` | 正常启动;窗口显示环境检查过程,成功后 3 秒自动关闭并打开浏览器 |
| `Maple Agent 启动 Debug.bat` | 调试模式;窗口保持打开,结束时显示 Press Enter to exit |
| `launcher\launcher.log` | 启动日志(时间 / 环境检查 / Python 路径 / WebUI 地址) |

## 3. 常见错误

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 提示"未检测到 Python" | Python 未安装或未加入 PATH | 安装 Python 3.11+ 并勾选 Add to PATH |
| 提示"未找到项目虚拟环境(.venv)" | 未运行 setup.ps1 | 运行 `scripts\setup.ps1` |
| 提示"依赖缺失" | 依赖未安装 | 运行 `scripts\setup.ps1` |
| ExecutionPolicy 阻止脚本 | 系统执行策略限制 | 用 bat 启动(已自动 Bypass),或运行 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| 窗口一闪而过、无反馈 | 旧版本 bat 中文编码问题 | 更新到最新代码(已修复为 GBK 编码);用 Debug.bat 查看错误 |
| 浏览器未自动打开 | 默认浏览器未关联 / 服务未就绪 | 手动访问 http://127.0.0.1:8080;查看 launcher.log |
| 端口 8080 被占用 | 其他程序占用 | 关闭占用程序,或 `python -m maple_agent start --port 8081` |

## 4. Debug 方式

1. 双击 `launcher\Maple Agent 启动 Debug.bat`,窗口保持打开可看完整日志;
2. 查看 `launcher\launcher.log`;
3. 查看运行日志:`logs\startup.log`、`logs\agent.log`、`logs\runtime.log` 等;
4. 命令行自检:`python -m maple_agent doctor`;
5. 复现问题时保留以上日志提供给维护者。

## 5. 注意事项

- API Key 只填写在本机 `.env`(不会进入 git / 审核包);
- 审核包生成:运行 `scripts\create_review_package.ps1`;
- Phase 0 Release 说明见 [06-phase0-release.md](06-phase0-release.md)。
