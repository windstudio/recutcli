# Recut: Kickstarter 视频自动剪辑工具设计

## 概述

**工具名称**：`recut`

**核心功能**：从 Kickstarter 项目页面自动下载视频，识别精彩片段，合并生成25秒社交媒体短视频。

**使用方式**：
```bash
recut https://kickstarter.com/projects/xxx -o output.mp4
```

可选参数：
```bash
--platform {tiktok,instagram,reels}  # 默认 tiktok
--scene-threshold 0.3                # 场景切换敏感度
```

---

## 技术架构

### 核心依赖

- `ffmpeg` - 视频处理（m3u8下载、场景检测、剪辑、合并、转码）
- `Python 3.10+` - 主程序逻辑
- `requests` + `beautifulsoup4` - 抓取页面提取 m3u8 URL
- `ffmpeg-python` - ffmpeg 的 Python 封装

### 处理流程

```
Kickstarter URL → 抓取页面 → 提取m3u8 → 下载并合并ts切片 → 场景检测 → 片段评分 → 选择Top片段 → 拼接 → 格式转换 → 输出
```

---

## 模块设计

```
recut/
├── __init__.py
├── cli.py           # 命令行入口
├── scraper.py       # Kickstarter页面抓取，提取m3u8
├── downloader.py    # m3u8下载与ts合并
├── analyzer.py      # 场景检测与片段评分
├── editor.py        # 视频剪辑、拼接、转码
└── config.py        # 平台预设配置（分辨率、码率等）
```

---

## 平台预设配置

| 平台 | 分辨率 | 比例 | 最大时长 |
|------|--------|------|----------|
| TikTok | 1080x1920 | 9:16 | 25s |
| Instagram Reels | 1080x1920 | 9:16 | 25s |
| Instagram Story | 1080x1920 | 9:16 | 25s |

---

## 片段评分算法

### 场景检测

- 使用 ffmpeg `select='gt(scene,0.3)'` 检测场景切换点
- 默认阈值 0.3（可通过参数调整）

### 评分规则

每个检测到的片段按以下规则评分：

1. **场景变化分**：片段内场景切换次数 / 片段时长（变化越密集越精彩）
2. **时长惩罚**：过短（<2s）或过长（>10s）的片段扣分

### 选择逻辑

- 按评分排序，选择 Top N 个片段
- 总时长精确控制在 25 秒
- 按原视频时间顺序排列（非评分顺序）

---

## 错误处理

### 网络错误

- Kickstarter 页面无法访问 → 提示错误并退出
- m3u8 下载失败 → 支持断点续传，失败后重试3次

### 视频处理

- 视频总时长 < 25秒 → 直接输出原视频（添加警告）
- 无法检测到场景切换 → 按固定间隔切分（如每5秒一段）
- 输出文件已存在 → 覆盖（添加 `--no-overwrite` 参数可选）

### 依赖检查

- 启动时检查 ffmpeg 是否安装 → 未安装则提示安装方法

---

## 测试策略

### 手动测试

- 准备 2-3 个真实 Kickstarter 项目 URL 进行端到端测试
- 验证输出视频时长精确为 25 秒
- 验证输出格式符合 TikTok 要求

### 单元测试（可选）

- m3u8 URL 提取逻辑
- 评分算法正确性
- 时长控制精度
