# 项目指令(AGENTS.md)

## 工作完成后的 GitHub 同步(必须执行)

- 每次完成任务/里程碑、提交代码后,**必须**同步推送到 GitHub 远程仓库 `origin`(分支 `main`);
- 推送命令:`git push origin main`;首次或分支变化时用 `git push -u origin $(git branch --show-current)`;
- 提交信息遵循既有约定:附修改文件列表、测试结果、运行/错误日志、下一步建议;
- 敏感信息(API Key、`.env`、日志、本地绝对路径、审核包产物)禁止进入仓库(已由 `.gitignore` 覆盖);
- 仓库地址:https://github.com/Yokoo3431/Maple-AI-Companion-Agent
