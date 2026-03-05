# 中文配音短视频功能设计

## 概述

扩展 recut 工具，自动将英文 Kickstarter 视频转换为带中文配音和字幕的 25 秒短视频。

## 数据流

```
原始视频
    ↓
[剪辑] → 25秒短视频
    ↓
[Whisper] → 英文转写文本
    ↓
[GLM-5] → 中文口播文案 (3秒钩子 + 中间 + 总结)
    ↓
[Piper TTS] → 中文配音音频
    ↓
[Whisper] → SRT 字幕 (对配音转写)
    ↓
[校对] → 修正 SRT (以文案为准)
    ↓
[FFmpeg] → 最终视频 (原音频混合 + 配音 + 字幕)
```

## 模块设计

### 1. `translator.py` - GLM-5 翻译

```python
def translate_and_refine(english_text: str, api_key: str) -> str:
    """翻译英文并提炼成25秒中文口播文案

    Args:
        english_text: 英文转写文本
        api_key: 元景 API Key

    Returns:
        中文口播文案（约25秒时长，3秒钩子+中间内容+最后总结结构）
    """
```

**API 配置**:
- URL: `https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1`
- Model: `glm-5`
- 使用 OpenAI Python SDK 兼容模式

**Prompt 设计**:
```
你是一位专业的短视频文案创作者。请将以下英文内容翻译成中文，并提炼成一段25秒的短视频口播文案。

要求：
1. 采用"3秒钩子+中间内容+最后总结"的结构
2. 语言口语化，适合短视频节奏
3. 总字数控制在70-90字（约25秒语速）

英文内容：
{english_text}
```

### 2. `tts.py` - Piper TTS

```python
def generate_audio(
    text: str,
    output_path: Path,
    voice: str = "zh_CN-huayan-medium"
) -> Path:
    """生成中文配音音频

    Args:
        text: 中文文案
        output_path: 输出音频路径 (.wav)
        voice: Piper 音色模型

    Returns:
        生成的音频文件路径
    """
```

**Piper 配置**:
- 包: `piper-tts`
- 默认音色: `zh_CN-huayan-medium`（中文女声）
- 支持用户通过环境变量或配置切换音色

### 3. `subtitle.py` - 字幕生成与校对

```python
def generate_srt(audio_path: Path, output_path: Path, model: str = "small") -> Path:
    """用 Whisper 生成 SRT 字幕

    Args:
        audio_path: 音频文件路径
        output_path: 输出 SRT 路径
        model: Whisper 模型大小

    Returns:
        生成的 SRT 文件路径
    """

def align_subtitle(
    srt_path: Path,
    expected_text: str,
    output_path: Path
) -> Path:
    """校对字幕，以原文案为准

    Args:
        srt_path: 原 SRT 文件
        expected_text: 期望的正确文案
        output_path: 输出 SRT 路径

    Returns:
        修正后的 SRT 文件路径
    """
```

**校对策略**:
- 比较 Whisper 转写结果与原文案
- 保留时间戳，替换文字内容
- 如有差异，以原文案为准

### 4. `editor.py` 扩展

```python
def merge_video_audio_subtitle(
    video_path: Path,
    original_audio_path: Path,  # 原视频音频
    dubbing_audio_path: Path,   # 配音音频
    subtitle_path: Path,
    output_path: Path,
    dubbing_volume: float = 1.0,
    original_volume: float = 0.3
) -> Path:
    """合成最终视频：混合原音频+配音+字幕

    Args:
        video_path: 视频文件
        original_audio_path: 原视频音频
        dubbing_audio_path: 配音音频
        subtitle_path: SRT 字幕文件
        output_path: 输出文件
        dubbing_volume: 配音音量
        original_volume: 原音频音量（降低作为背景）

    Returns:
        最终视频文件路径
    """
```

**FFmpeg 命令**:
```
ffmpeg -i video.mp4 -i dubbing.wav -i original.wav \
  -filter_complex "[1:a]volume=1.0[voice];[2:a]volume=0.3[bg];[voice][bg]amix=inputs=2[aout]" \
  -vf "subtitles=subtitle.srt" \
  -map 0:v -map "[aout]" output.mp4
```

### 5. `config.py` 扩展

```python
@dataclass
class TTSConfig:
    """TTS 配置"""
    voice: str = "zh_CN-huayan-medium"
    whisper_model: str = "small"

@dataclass
class APIConfig:
    """API 配置"""
    yuanjing_api_key: str = ""  # 从环境变量读取
    yuanjing_base_url: str = "https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1"
```

### 6. CLI 流程更新

```python
# cli.py 主流程
def main(url, output, platform, scene_threshold, m3u8_url):
    # 1. 下载视频
    # 2. 剪辑短视频
    # 3. Whisper 转写英文
    # 4. GLM-5 翻译+提炼 (新增)
    # 5. Piper TTS 生成配音 (新增)
    # 6. Whisper 生成 SRT (新增)
    # 7. 校对字幕 (新增)
    # 8. FFmpeg 合成 (新增)
    # 9. 保存原视频、转写文本、最终视频
```

## 依赖新增

```toml
[project.dependencies]
openai = ">=1.0.0"
piper-tts = ">=1.0.0"
```

## 输出文件

| 文件 | 说明 |
|------|------|
| `{output}.mp4` | 最终带配音字幕的短视频 |
| `{output}_orig.mp4` | 原始下载视频 |
| `{output}_script.md` | 英文转写文本 |
| `{output}_chinese.md` | 中文口播文案 |
| `{output}.srt` | 字幕文件 |

## 环境变量

| 变量 | 说明 |
|------|------|
| `YUANJING_API_KEY` | 元景 API Key |
| `PIPER_VOICE` | Piper 音色（可选，默认 zh_CN-huayan-medium） |

## 错误处理

- API Key 未配置：提示用户设置环境变量
- Piper 模型下载失败：提供手动下载指引
- 音频时长超限：警告并截断或调整语速
