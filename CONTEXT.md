# Recut CLI 领域上下文

> 本文件记录**当前真实行为**。`docs/plans/` 下的设计文档是历史档案，与现状冲突时以本文件和源码为准（2026-08-24 全源码审查后整理）。

## 项目定位

把 Kickstarter（或任意 URL）的项目视频自动剪辑为中文配音的竖版社交媒体短视频：抓取 → 下载 → 场景/运动分析 → Whisper 转写 → LLM 生成中文文案+标题+标签 → TTS 配音 → 字幕对齐 → 封面图 → 合成（含片尾）。

## 核心概念词汇表

| 术语 | 含义 |
|------|------|
| **raw video** (`*_raw.mp4`) | 原始下载的完整视频，存于 checkpoint 目录 |
| **fragment / scene** | 场景检测切出的片段，由 `Scene(start, end, motion_intensity)` 表示 |
| **motion_intensity** | 片段运动强度 ×100 的整数（历史名 `score_change_count`，scenes.json 读取时向后兼容）。评分 = 运动强度 × 时长惩罚 |
| **nodub video** (`*_nodub.mp4`) | 无配音的中间短视频（按平台尺寸裁剪拼接后） |
| **dubbing** (`*_dubbing.wav`) | TTS 生成的中文配音音频 |
| **checkpoint 目录** | `output/<name>/`，存放所有中间产物；最终成品在 `output/<name>.mp4`，脚本+元数据在 `output/<name>.md` |
| **resume 模式** | `--pause-on-chs-script` 在生成中文脚本后暂停；用户审校编辑后用 `--resume <md路径或目录>` 续跑 |

## 关键决策记录（ADR 摘要）

- **运动评分取代场景切换计数**（2026-03-24）：场景边界即变化点，片段内计数恒为 1，无区分度。改为抽帧平均像素差作为运动强度。
- **TTS 引擎演进**：Piper（效果差，已移除）→ Coqui（可选，依赖为 `recut[tts-coqui]` extra）→ 默认 edge-tts → MiniMax API（音量 vol=3.0，voice_id 经 `.env` 配置）。
- **口播字数校准**：按 TTS 引擎语速（`TTS_CHAR_RATES`）从目标时长推算字数区间，LLM 输出超限自动重写重试（最多 3 次）。
- **封面图主图缩放 1.1×**画布宽（2026-03-30 定稿；1.2× 会裁掉左右边缘过多）。
- **LLM 配置只经 `.env`**（`LLM_API_KEY`/`LLM_API_URL`/`LLM_MODEL`）；`YUANJING_API_KEY` 兼容已删除（03-06 决策）。
- **输出基目录固定为 `output/`**，`-o` 相对路径都落在其下。

## 已废弃的历史需求（勿再实现）

来自最早的 2026-03-01 设计文档、经用户确认处置（2026-08-24）：

- ~~m3u8 断点续传~~ — 废弃（重试 3 次已够用）
- ~~"总时长 <25s 直接输出原视频"~~ — 已被时长参数化逻辑取代；现行行为是：可用片段不足目标时长时**警告**并继续（cli.py `_run_remaining_phases`）
- `--no-overwrite` — 已于 2026-08 实现（默认覆盖，加该参数则输出已存在时报错退出）

## 环境注意

- ffmpeg 用系统二进制（`downloader.get_ffmpeg_path()`，imageio-ffmpeg 兜底），不用 ffmpeg-python 库
- Whisper 转写默认 small 模型（`WHISPER_MODEL` 可配），首次运行会下载 ~460MB 到 `~/.cache/whisper`
- 《docs/优化需求.txt》是 GBK 编码的需求日志（已被 .gitignore 忽略），仅作历史参考
