# Recut 全源码审查优化方案（2026-08-24）

基于双轴审查结果（Standards + Spec），结合《优化需求.txt》需求日志修订分类。
原则：以最新源码功能为准；只修真问题；历史设计文档不再作为规格依据。

**执行状态：全部完成（2026-08-25）。最终验证：91 个测试全绿（.venv, Python 3.12 + uv 创建）。
新增回归测试缺口：subprocess 失败路径、--no-overwrite 行为未配专门测试（见 Review 备注）。**

## Phase 1 — 缺陷修复（P0，必须做）

- [x] 1.1 analyzer.py 五处 subprocess.run 增加错误检查——统一改用
      downloader.run_ffmpeg() 共享助手（失败抛 RuntimeError 附 stderr 尾部 500 字符）
- [x] 1.2 tts.py 硬编码 "ffmpeg" 改用 downloader.get_ffmpeg_path()
- [x] 1.3 checkpoint.py 编码回退：except 同时捕获 UnicodeDecodeError 和 json.JSONDecodeError
      （load_scenes 已随死代码删除，修复落在 load_metadata）
- [x] 1.4 cli.py 合并失败时清理遗留的 {stem}_temp.mp4
- [x] 1.5 translator.py / tts.py / subtitle.py 宽 except 双重包裹：
      RuntimeError 直接 re-raise，其余异常 raise ... from e 保留原始链
- [x] 1.6 subtitle.py SRT 解析失败块计数并打印一次警告（含空 block）

## Phase 1.5 — 用户确认要实现的功能（P0，原设计复活）

- [x] N1 --no-overwrite 参数：默认覆盖；加该参数且输出已存在时 _exit_on_error 报错。
      README options 表已补充该行
- [x] N2 短视频兜底警告：片段总时长 < 目标时长时输出 Warning 并继续
      （取代原设计的"直接输出原视频"，符合现行时长参数化逻辑）

## Phase 2 — 依赖治理（P0）

- [x] 2.1 pyproject.toml 删除 ffmpeg-python
- [x] 2.2 显式声明 numpy>=1.24.0
- [x] 2.3 Coqui TTS 移入 optional-dependencies tts-coqui；
      _generate_coqui_audio 懒导入失败时报错并提示安装命令

## Phase 3 — 死代码与重复消除（P1）

- [x] 3.1 删 checkpoint.py save_scenes/load_scenes（连同不再使用的 Scene/asdict import）
- [x] 3.2 删 thumbnail.py 三个无调用函数（create_gradient_mask/draw_text_with_shadow/
      draw_text_with_stroke，共 -101 行）
- [x] 3.3 删 cli.py 未使用的 import shutil
- [x] 3.4 editor.py 提取 _merge_with_audio（logo/无 logo 分支共享）+
      _build_subtitle_filter；thumbnail/no-thumbnail 两路径复用，净删 ~80 行
- [x] 3.5 test_cli_integration.py 提取 _make_mock_side_effects/_patch_cli_pipeline helper，
      并补上遗漏的 get_video_duration mock

## Phase 4 — 命名与结构（P1-P2，判断性）

- [x] 4.1 Scene.score_change_count → motion_intensity（源码+测试+README；
      scenes.json 读取兼容旧字段名 score_change_count）
- [x] 4.2 （暂缓）元数据裸 dict → dataclass：收益有限，待下次触碰该代码时顺带做
- [x] 4.3 （不做）_run_remaining_phases 13 参数聚合：改动面大收益小

## Phase 5 — 文档对齐（P1）

- [x] 5.1 README MiniMax 音量 2.0 → 3.0
- [x] 5.2 README 字幕延迟描述修正（仅有 thumbnail 时偏移 0.5s）
- [x] 5.3 新建 CONTEXT.md：词汇表 + 决策记录 + 废弃需求清单，标注 docs/plans/* 为历史档案
- [x] 5.4 三项原设计错误处理处置已记录于 CONTEXT.md：
      --no-overwrite → 已实现；m3u8 断点续传 → 废弃；<25s 兜底 → 以警告形式实现

## 杂项

- [x] 删除仓库根目录误生成的 `-` 文件（74KB，2026-03-24 生成）
- [x] .venv 加入 .gitignore（已有）；用 uv 创建 Python 3.12 venv 作为测试环境

## Review（完成后复盘）

- 测试环境曾缺 pytest/whisper/numpy（Python314 全新无包），用 `uv venv --python 3.12`
  重建并 `uv pip install -e .` 解决；whisper small 模型首次运行下载了 ~460MB
- 集成测试两例因 get_video_duration 未 mock 而失败——这正是 1.1 修复暴露的测试缺口
  （旧代码对坏文件静默返回 0.0，新代码正确抛错），已在重构 mock 栈时补上
- 遗留建议（低优先）：为 run_ffmpeg 的失败路径和 --no-overwrite 各补一个单测；
  《优化需求.txt》中的明文 API Key 建议尽快在平台轮换
