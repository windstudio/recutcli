# CLAUDE.md

Recut CLI — Kickstarter 视频自动剪辑为中文配音短视频的 CLI 工具。
仓库：https://github.com/windstudio/recutcli（包名 `recut-cli`，命令仍为 `recut`）。
技术栈：Python 3.10+ / click / ffmpeg (subprocess) / whisper / openai / edge-tts / Pillow。

（后续可补充构建命令与架构说明）

## Agent skills

### Issue tracker

Issues 以本地 markdown 文件形式存于 `.scratch/<feature>/`。See `docs/agents/issue-tracker.md`.

### Triage labels

使用五个默认 triage 角色，标签字符串即角色名。See `docs/agents/triage-labels.md`.

### Domain docs

单上下文布局：仓库根一个 `CONTEXT.md` + `docs/adr/` 存 ADR。See `docs/agents/domain.md`.
