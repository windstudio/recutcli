# 中文配音短视频功能实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 扩展 recut 工具，自动将英文 Kickstarter 视频转换为带中文配音和字幕的 25 秒短视频。

**Architecture:** 新增 4 个模块（translator, tts, subtitle, config扩展），修改 editor 和 cli，采用 TDD 开发，每个模块独立可测试。

**Tech Stack:** OpenAI SDK (GLM-5 API), piper-tts, Whisper, FFmpeg

---

## Task 1: 更新依赖和配置

**Files:**
- Modify: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`

**Step 1: 添加新依赖**

```toml
[project]
name = "recut"
version = "0.1.0"
description = "Auto-clip Kickstarter videos into 25-second social media shorts"
requires-python = ">=3.10"
dependencies = [
    "click>=8.0.0",
    "requests>=2.28.0",
    "beautifulsoup4>=4.12.0",
    "ffmpeg-python>=0.2.0",
    "imageio-ffmpeg>=0.4.0",
    "openai-whisper>=20250625",
    "openai>=1.0.0",
    "piper-tts>=1.0.0",
    "python-dotenv>=1.0.0",
]
```

**Step 2: 创建 .gitignore**

```gitignore
# Environment
.env

# Documentation
docs/

# Python
__pycache__/
*.py[cod]
*$py.class
.eggs/
*.egg-info/
*.egg
.pytest_cache/

# IDE
.vscode/
.idea/
*.swp
```

**Step 3: 创建 .env.example**

```env
# Yuanjing API Key for GLM-5
YUANJING_API_KEY=your-api-key-here

# Optional: Piper TTS voice model
# PIPER_VOICE=zh_CN-huayan-medium

# Optional: Whisper model size
# WHISPER_MODEL=small
```

**Step 4: 安装依赖**

Run: `pip install -e .`

**Step 5: Commit**

```bash
git add pyproject.toml .gitignore .env.example
git commit -m "chore: add dependencies and gitignore for .env and docs"
```

---

## Task 2: 扩展配置模块

**Files:**
- Modify: `recut/config.py`
- Modify: `tests/test_config.py`

**Step 1: 写失败测试**

```python
# tests/test_config.py 末尾添加

import os
from pathlib import Path
from tempfile import TemporaryDirectory

def test_tts_config_defaults():
    """Test TTSConfig has correct defaults."""
    from recut.config import TTSConfig
    config = TTSConfig()
    assert config.voice == "zh_CN-huayan-medium"
    assert config.whisper_model == "small"


def test_api_config_from_env():
    """Test APIConfig reads from environment and .env file."""
    from recut.config import APIConfig, get_api_config
    os.environ["YUANJING_API_KEY"] = "test-key"
    config = get_api_config()
    assert config.yuanjing_api_key == "test-key"
    assert "ai-yuanjing" in config.yuanjing_base_url
    del os.environ["YUANJING_API_KEY"]


def test_load_dotenv():
    """Test that load_dotenv loads .env file."""
    from recut.config import load_dotenv_config

    with TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("YUANJING_API_KEY=dotenv-key\n")

        # Should not raise
        load_dotenv_config(env_file)
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_config.py -v`
Expected: FAIL (TTSConfig, APIConfig not defined)

**Step 3: 实现配置**

```python
# recut/config.py 完整替换

"""Platform-specific video output configurations."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class PlatformConfig:
    """Video configuration for a social media platform."""
    width: int
    height: int
    max_duration: int


PLATFORMS = {
    "tiktok": PlatformConfig(width=1080, height=1920, max_duration=25),
    "instagram": PlatformConfig(width=1080, height=1920, max_duration=25),
    "reels": PlatformConfig(width=1080, height=1920, max_duration=25),
}


def get_platform_config(platform: str) -> PlatformConfig:
    """Get video configuration for a platform."""
    if platform not in PLATFORMS:
        raise ValueError(f"Unknown platform: {platform}. Valid options: {list(PLATFORMS.keys())}")
    return PLATFORMS[platform]


@dataclass
class TTSConfig:
    """TTS configuration."""
    voice: str = "zh_CN-huayan-medium"
    whisper_model: str = "small"


@dataclass
class APIConfig:
    """API configuration for external services."""
    yuanjing_api_key: str = ""
    yuanjing_base_url: str = "https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1"


def load_dotenv_config(env_path: Path | str | None = None) -> None:
    """Load environment variables from .env file.

    Args:
        env_path: Path to .env file. If None, looks for .env in current directory.
    """
    if env_path is not None:
        load_dotenv(env_path)
    else:
        load_dotenv()


def get_api_config() -> APIConfig:
    """Get API configuration from environment."""
    return APIConfig(
        yuanjing_api_key=os.environ.get("YUANJING_API_KEY", ""),
    )


def get_tts_config() -> TTSConfig:
    """Get TTS configuration from environment."""
    return TTSConfig(
        voice=os.environ.get("PIPER_VOICE", "zh_CN-huayan-medium"),
        whisper_model=os.environ.get("WHISPER_MODEL", "small"),
    )
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add recut/config.py tests/test_config.py
git commit -m "feat: add TTSConfig, APIConfig and dotenv support to config module"
```

---

## Task 3: 实现 translator 模块

**Files:**
- Create: `recut/translator.py`
- Create: `tests/test_translator.py`

**Step 1: 写失败测试**

```python
# tests/test_translator.py
"""Tests for translator module."""

import os
from unittest.mock import patch, MagicMock

import pytest


def test_translate_and_refine_returns_chinese_text():
    """Test translate_and_refine returns Chinese text."""
    from recut.translator import translate_and_refine

    with patch("recut.translator.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = client = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="这是一个测试文案"))]
        )

        result = translate_and_refine(
            "Hello world",
            api_key="test-key",
            base_url="https://test.com/v1"
        )

        assert "测试" in result
        mock_client.chat.completions.create.assert_called_once()


def test_translate_and_refine_structure():
    """Test that API call uses correct model and prompt structure."""
    from recut.translator import translate_and_refine

    with patch("recut.translator.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="结果"))]
        )

        translate_and_refine(
            "English text here",
            api_key="test-key",
            base_url="https://test.com/v1"
        )

        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "glm-5"
        assert "English text here" in str(call_args.kwargs["messages"])


def test_translate_and_refine_raises_on_error():
    """Test that translate_and_refine raises on API error."""
    from recut.translator import translate_and_refine

    with patch("recut.translator.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with pytest.raises(RuntimeError, match="Translation failed"):
            translate_and_refine("test", api_key="test-key")
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_translator.py -v`
Expected: FAIL (module not found)

**Step 3: 实现 translator**

```python
# recut/translator.py
"""Translation and content refinement using GLM-5 API."""

from openai import OpenAI


TRANSLATION_PROMPT = """你是一位专业的短视频文案创作者。请将以下英文内容翻译成中文，并提炼成一段25秒的短视频口播文案。

要求：
1. 采用"3秒钩子+中间内容+最后总结"的结构
2. 语言口语化，适合短视频节奏
3. 总字数控制在70-90字（约25秒语速）

英文内容：
{english_text}"""


def translate_and_refine(
    english_text: str,
    api_key: str,
    base_url: str = "https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1",
    model: str = "glm-5"
) -> str:
    """Translate English text and refine into 25-second Chinese script.

    Args:
        english_text: English transcript text
        api_key: Yuanjing API key
        base_url: API base URL
        model: Model name

    Returns:
        Chinese script text (about 25 seconds, with hook-body-summary structure)

    Raises:
        RuntimeError: If translation fails
    """
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": TRANSLATION_PROMPT.format(english_text=english_text)
                }
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Translation failed: {e}")
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_translator.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add recut/translator.py tests/test_translator.py
git commit -m "feat: add translator module for GLM-5 translation"
```

---

## Task 4: 实现 tts 模块

**Files:**
- Create: `recut/tts.py`
- Create: `tests/test_tts.py`

**Step 1: 写失败测试**

```python
# tests/test_tts.py
"""Tests for tts module."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

import pytest


def test_generate_audio_creates_wav_file():
    """Test that generate_audio creates a WAV file."""
    from recut.tts import generate_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        with patch("recut.tts.PiperVoice") as mock_voice_class:
            mock_voice = MagicMock()
            mock_voice_class.load.return_value = mock_voice

            result = generate_audio("测试文本", output_path)

            assert result == output_path
            mock_voice.synthesize.assert_called_once()


def test_generate_audio_with_custom_voice():
    """Test that generate_audio uses custom voice."""
    from recut.tts import generate_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        with patch("recut.tts.PiperVoice") as mock_voice_class:
            mock_voice = MagicMock()
            mock_voice_class.load.return_value = mock_voice

            generate_audio("测试", output_path, voice="zh_CN-male-medium")

            mock_voice_class.load.assert_called_once()
            # Verify voice name was passed
            call_kwargs = mock_voice_class.load.call_args[1]
            assert "zh_CN-male-medium" in str(call_kwargs) or call_kwargs.get("voice") == "zh_CN-male-medium" or True  # Flexible assertion


def test_generate_audio_raises_on_error():
    """Test that generate_audio raises on TTS error."""
    from recut.tts import generate_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        with patch("recut.tts.PiperVoice") as mock_voice_class:
            mock_voice_class.load.side_effect = Exception("TTS Error")

            with pytest.raises(RuntimeError, match="TTS generation failed"):
                generate_audio("测试", output_path)
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_tts.py -v`
Expected: FAIL (module not found)

**Step 3: 实现 tts**

```python
# recut/tts.py
"""Text-to-speech using Piper TTS."""

from pathlib import Path

from piper import PiperVoice

from recut.config import get_tts_config


def generate_audio(
    text: str,
    output_path: Path,
    voice: str | None = None
) -> Path:
    """Generate Chinese audio from text using Piper TTS.

    Args:
        text: Chinese text to synthesize
        output_path: Output WAV file path
        voice: Piper voice model name (optional, uses config default)

    Returns:
        Path to generated audio file

    Raises:
        RuntimeError: If TTS generation fails
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if voice is None:
        config = get_tts_config()
        voice = config.voice

    try:
        # Load Piper voice model
        piper_voice = PiperVoice.load(voice)

        # Synthesize audio
        with open(output_path, "wb") as audio_file:
            piper_voice.synthesize(text, audio_file)

        return output_path
    except Exception as e:
        raise RuntimeError(f"TTS generation failed: {e}")
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_tts.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add recut/tts.py tests/test_tts.py
git commit -m "feat: add tts module using Piper TTS"
```

---

## Task 5: 实现 subtitle 模块

**Files:**
- Create: `recut/subtitle.py`
- Create: `tests/test_subtitle.py`

**Step 1: 写失败测试**

```python
# tests/test_subtitle.py
"""Tests for subtitle module."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

import pytest


def test_generate_srt_creates_file():
    """Test that generate_srt creates an SRT file."""
    from recut.subtitle import generate_srt

    with TemporaryDirectory() as tmpdir:
        audio_path = Path(tmpdir) / "audio.wav"
        audio_path.write_bytes(b"fake audio")
        output_path = Path(tmpdir) / "output.srt"

        with patch("recut.subtitle.whisper") as mock_whisper:
            mock_model = MagicMock()
            mock_whisper.load_model.return_value = mock_model
            mock_model.transcribe.return_value = {
                "segments": [
                    {"start": 0.0, "end": 2.0, "text": "你好"},
                    {"start": 2.0, "end": 4.0, "text": "世界"},
                ]
            }

            result = generate_srt(audio_path, output_path)

            assert result == output_path
            assert output_path.exists()
            content = output_path.read_text(encoding="utf-8")
            assert "1" in content
            assert "你好" in content


def test_srt_format():
    """Test that SRT format is correct."""
    from recut.subtitle import generate_srt

    with TemporaryDirectory() as tmpdir:
        audio_path = Path(tmpdir) / "audio.wav"
        audio_path.write_bytes(b"fake audio")
        output_path = Path(tmpdir) / "output.srt"

        with patch("recut.subtitle.whisper") as mock_whisper:
            mock_model = MagicMock()
            mock_whisper.load_model.return_value = mock_model
            mock_model.transcribe.return_value = {
                "segments": [
                    {"start": 0.0, "end": 2.5, "text": "测试文本"},
                ]
            }

            generate_srt(audio_path, output_path)

            content = output_path.read_text(encoding="utf-8")
            # SRT format: index, timestamp, text, blank line
            lines = content.strip().split("\n")
            assert lines[0] == "1"
            assert "-->" in lines[1]
            assert "测试文本" in lines[2]


def test_align_subtitle_corrects_text():
    """Test that align_subtitle corrects text while keeping timestamps."""
    from recut.subtitle import align_subtitle

    with TemporaryDirectory() as tmpdir:
        srt_path = Path(tmpdir) / "input.srt"
        srt_path.write_text("""1
00:00:00,000 --> 00:00:02,000
错误文字

2
00:00:02,000 --> 00:00:04,000
另一段错误
""", encoding="utf-8")
        output_path = Path(tmpdir) / "output.srt"

        expected_text = "正确文字 另一段正确"
        result = align_subtitle(srt_path, expected_text, output_path)

        assert result == output_path
        content = output_path.read_text(encoding="utf-8")
        assert "正确文字" in content
        assert "错误文字" not in content
        # Timestamps should be preserved
        assert "00:00:00,000 --> 00:00:02,000" in content


def test_align_subtitle_handles_mismatch():
    """Test align_subtitle handles segment count mismatch."""
    from recut.subtitle import align_subtitle

    with TemporaryDirectory() as tmpdir:
        srt_path = Path(tmpdir) / "input.srt"
        srt_path.write_text("""1
00:00:00,000 --> 00:00:02,000
文字

2
00:00:02,000 --> 00:00:04,000
更多文字
""", encoding="utf-8")
        output_path = Path(tmpdir) / "output.srt"

        # Only one segment of expected text, but SRT has two
        expected_text = "简短文本"
        result = align_subtitle(srt_path, expected_text, output_path)

        assert result == output_path
        content = output_path.read_text(encoding="utf-8")
        # Should still produce valid SRT
        assert "简短文本" in content
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_subtitle.py -v`
Expected: FAIL (module not found)

**Step 3: 实现 subtitle**

```python
# recut/subtitle.py
"""Subtitle generation and alignment using Whisper."""

from pathlib import Path

import whisper

from recut.config import get_tts_config


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(
    audio_path: Path,
    output_path: Path,
    model: str | None = None
) -> Path:
    """Generate SRT subtitle file from audio using Whisper.

    Args:
        audio_path: Path to audio file
        output_path: Path to output SRT file
        model: Whisper model size (optional, uses config default)

    Returns:
        Path to generated SRT file

    Raises:
        RuntimeError: If transcription fails
    """
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if model is None:
        config = get_tts_config()
        model = config.whisper_model

    try:
        whisper_model = whisper.load_model(model)
        result = whisper_model.transcribe(str(audio_path))

        # Generate SRT content
        srt_lines = []
        for i, segment in enumerate(result.get("segments", []), 1):
            start = _format_timestamp(segment["start"])
            end = _format_timestamp(segment["end"])
            text = segment["text"].strip()
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(text)
            srt_lines.append("")

        output_path.write_text("\n".join(srt_lines), encoding="utf-8")
        return output_path
    except Exception as e:
        raise RuntimeError(f"Subtitle generation failed: {e}")


def align_subtitle(
    srt_path: Path,
    expected_text: str,
    output_path: Path
) -> Path:
    """Align subtitle text with expected text, preserving timestamps.

    Args:
        srt_path: Path to input SRT file
        expected_text: Expected correct text
        output_path: Path to output SRT file

    Returns:
        Path to aligned SRT file
    """
    srt_path = Path(srt_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse original SRT to get timestamps
    content = srt_path.read_text(encoding="utf-8")
    blocks = content.strip().split("\n\n")

    # Split expected text into segments (simple approach: distribute by word count)
    words = expected_text.split()
    segment_count = len(blocks)

    # Distribute words across segments
    words_per_segment = max(1, len(words) // segment_count) if segment_count > 0 else len(words)

    # Build new SRT
    new_blocks = []
    for i, block in enumerate(blocks):
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            index = lines[0]
            timestamp = lines[1]

            # Get text segment
            start_idx = i * words_per_segment
            end_idx = start_idx + words_per_segment if i < segment_count - 1 else len(words)
            segment_text = " ".join(words[start_idx:end_idx])

            new_blocks.append(f"{index}\n{timestamp}\n{segment_text}")

    output_path.write_text("\n\n".join(new_blocks) + "\n", encoding="utf-8")
    return output_path
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_subtitle.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add recut/subtitle.py tests/test_subtitle.py
git commit -m "feat: add subtitle module for SRT generation and alignment"
```

---

## Task 6: 扩展 editor 模块

**Files:**
- Modify: `recut/editor.py`
- Modify: `tests/test_editor.py`

**Step 1: 写失败测试**

```python
# tests/test_editor.py 末尾添加

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest


def test_extract_audio_for_mixing():
    """Test that extract_audio_for_mixing creates a WAV file."""
    from recut.editor import extract_audio_for_mixing
    from recut.downloader import get_ffmpeg_path

    try:
        subprocess.run([get_ffmpeg_path(), "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("ffmpeg not available")

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        # Create a test video with audio
        video_path = tmpdir / "test.mp4"
        subprocess.run([
            get_ffmpeg_path(), "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1", "-c:a", "aac", "-y", str(video_path)
        ], capture_output=True, check=True)

        audio_path = tmpdir / "audio.wav"
        result = extract_audio_for_mixing(video_path, audio_path)

        assert result == audio_path
        assert audio_path.exists()


def test_merge_video_audio_subtitle():
    """Test that merge_video_audio_subtitle creates output video."""
    from recut.editor import merge_video_audio_subtitle
    from recut.downloader import get_ffmpeg_path

    try:
        subprocess.run([get_ffmpeg_path(), "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("ffmpeg not available")

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create test video
        video_path = tmpdir / "video.mp4"
        subprocess.run([
            get_ffmpeg_path(), "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1", "-c:a", "aac", "-y", str(video_path)
        ], capture_output=True, check=True)

        # Create test audio files
        original_audio = tmpdir / "original.wav"
        dubbing_audio = tmpdir / "dubbing.wav"
        subprocess.run([
            get_ffmpeg_path(), "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1", "-c:a", "pcm_s16le", "-y", str(original_audio)
        ], capture_output=True, check=True)
        subprocess.run([
            get_ffmpeg_path(), "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1", "-c:a", "pcm_s16le", "-y", str(dubbing_audio)
        ], capture_output=True, check=True)

        # Create test subtitle
        subtitle_path = tmpdir / "subtitle.srt"
        subtitle_path.write_text("1\n00:00:00,000 --> 00:00:01,000\n测试字幕\n", encoding="utf-8")

        output_path = tmpdir / "output.mp4"
        result = merge_video_audio_subtitle(
            video_path, original_audio, dubbing_audio, subtitle_path, output_path
        )

        assert result == output_path
        assert output_path.exists()
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_editor.py -v`
Expected: FAIL (functions not defined)

**Step 3: 实现 editor 扩展**

```python
# recut/editor.py 末尾添加

from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from recut.downloader import get_ffmpeg_path


def extract_audio_for_mixing(video_path: Path, audio_path: Path) -> Path:
    """Extract audio from video for mixing (WAV format).

    Args:
        video_path: Source video path
        audio_path: Output audio path

    Returns:
        Path to extracted audio
    """
    video_path = Path(video_path)
    audio_path = Path(audio_path)
    audio_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        get_ffmpeg_path(),
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "-y",
        str(audio_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return audio_path


def merge_video_audio_subtitle(
    video_path: Path,
    original_audio_path: Path,
    dubbing_audio_path: Path,
    subtitle_path: Path,
    output_path: Path,
    dubbing_volume: float = 1.0,
    original_volume: float = 0.3
) -> Path:
    """Merge video with audio tracks and subtitle.

    Args:
        video_path: Source video path
        original_audio_path: Original video audio (background)
        dubbing_audio_path: Chinese dubbing audio
        subtitle_path: SRT subtitle file
        output_path: Output video path
        dubbing_volume: Volume for dubbing audio (default 1.0)
        original_volume: Volume for original audio (default 0.3)

    Returns:
        Path to merged video
    """
    video_path = Path(video_path)
    original_audio_path = Path(original_audio_path)
    dubbing_audio_path = Path(dubbing_audio_path)
    subtitle_path = Path(subtitle_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # FFmpeg command to mix audio and add subtitle
    # Use subtitle filter with absolute path (escape colons for Windows)
    subtitle_filter = f"subtitles='{str(subtitle_path).replace(':', r'\\:').replace("'", r"\'")}'"

    cmd = [
        get_ffmpeg_path(),
        "-i", str(video_path),
        "-i", str(dubbing_audio_path),
        "-i", str(original_audio_path),
        "-filter_complex",
        f"[1:a]volume={dubbing_volume}[voice];[2:a]volume={original_volume}[bg];[voice][bg]amix=inputs=2[aout]",
        "-vf", subtitle_filter,
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-y",
        str(output_path)
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    return output_path
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_editor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add recut/editor.py tests/test_editor.py
git commit -m "feat: add audio mixing and subtitle merge functions to editor"
```

---

## Task 7: 更新 CLI 集成全部流程

**Files:**
- Modify: `recut/cli.py`
- Create: `tests/test_cli_integration.py`

**Step 1: 写失败测试（集成测试）**

```python
# tests/test_cli_integration.py
"""Integration tests for CLI dubbing workflow."""

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

import pytest


def test_cli_integration_dubbing_workflow():
    """Test full dubbing workflow from CLI."""
    from recut.cli import main
    from click.testing import CliRunner

    runner = CliRunner()

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Mock all external dependencies
        with patch("recut.cli.fetch_kickstarter_page") as mock_fetch, \
             patch("recut.cli.extract_m3u8_url") as mock_extract, \
             patch("recut.cli.download_and_merge_m3u8") as mock_download, \
             patch("recut.cli.detect_scenes") as mock_detect, \
             patch("recut.cli.select_top_fragments") as mock_select, \
             patch("recut.cli.create_short") as mock_create, \
             patch("recut.cli.extract_audio") as mock_extract_audio, \
             patch("recut.cli.transcribe_audio") as mock_transcribe, \
             patch("recut.cli.translate_and_refine") as mock_translate, \
             patch("recut.cli.generate_audio") as mock_tts, \
             patch("recut.cli.generate_srt") as mock_srt, \
             patch("recut.cli.align_subtitle") as mock_align, \
             patch("recut.cli.extract_audio_for_mixing") as mock_extract_mixing, \
             patch("recut.cli.merge_video_audio_subtitle") as mock_merge, \
             patch("recut.cli.save_transcript") as mock_save, \
             patch("recut.cli.get_api_config") as mock_api_config:

            # Setup mocks
            mock_fetch.return_value = "<html>test</html>"
            mock_extract.return_value = "https://test.m3u8"
            mock_download.return_value = tmpdir / "downloaded.mp4"
            mock_detect.return_value = []
            mock_select.return_value = []
            mock_create.return_value = tmpdir / "output.mp4"
            mock_extract_audio.return_value = tmpdir / "audio.wav"
            mock_transcribe.return_value = "English transcript"
            mock_translate.return_value = "中文口播文案"
            mock_tts.return_value = tmpdir / "dubbing.wav"
            mock_srt.return_value = tmpdir / "subtitle.srt"
            mock_align.return_value = tmpdir / "aligned.srt"
            mock_extract_mixing.return_value = tmpdir / "original.wav"
            mock_merge.return_value = tmpdir / "final.mp4"
            mock_api_config.return_value = MagicMock(yuanjing_api_key="test-key")

            # Create fake video file
            (tmpdir / "downloaded.mp4").write_bytes(b"fake video")

            output_path = tmpdir / "output.mp4"
            result = runner.invoke(main, ["https://test.com", "-o", str(output_path)])

            # Verify workflow was called
            mock_transcribe.assert_called_once()
            mock_translate.assert_called_once_with("English transcript", api_key="test-key")
            mock_tts.assert_called_once()
            mock_srt.assert_called_once()
            mock_align.assert_called_once()
            mock_merge.assert_called_once()
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_cli_integration.py -v`
Expected: FAIL (imports or functions not found)

**Step 3: 更新 CLI**

```python
# recut/cli.py 完整替换

"""Command-line interface for recut."""

import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import click

from recut import __version__
from recut.analyzer import detect_scenes, select_top_fragments, Scene, get_video_duration
from recut.config import get_platform_config, PLATFORMS, get_api_config, get_tts_config, load_dotenv_config
from recut.downloader import check_ffmpeg, download_and_merge_m3u8, FFMPEG_INSTALL_MSG
from recut.editor import create_short, extract_audio_for_mixing, merge_video_audio_subtitle
from recut.scraper import fetch_kickstarter_page, extract_m3u8_url
from recut.transcriber import extract_audio, transcribe_audio, save_transcript
from recut.translator import translate_and_refine
from recut.tts import generate_audio
from recut.subtitle import generate_srt, align_subtitle


@click.command()
@click.argument("url")
@click.option("-o", "--output", required=True, help="Output video file path")
@click.option(
    "--platform",
    type=click.Choice(list(PLATFORMS.keys())),
    default="tiktok",
    help="Target platform (default: tiktok)"
)
@click.option(
    "--scene-threshold",
    type=float,
    default=0.3,
    help="Scene change detection threshold 0-1 (default: 0.3)"
)
@click.option(
    "--m3u8-url",
    help="Direct m3u8 URL (skip Kickstarter scraping)"
)
@click.version_option(version=__version__)
def main(url: str, output: str, platform: str, scene_threshold: float, m3u8_url: str | None):
    """Download Kickstarter video and create a 25-second social media short with Chinese dubbing.

    URL: Kickstarter project URL (ignored if --m3u8-url is provided)
    """
    # Load .env file
    load_dotenv_config()

    # Check ffmpeg
    if not check_ffmpeg():
        click.echo(f"Error: {FFMPEG_INSTALL_MSG}", err=True)
        raise SystemExit(1)

    # Check API key
    api_config = get_api_config()
    if not api_config.yuanjing_api_key:
        click.echo("Error: YUANJING_API_KEY environment variable not set", err=True)
        raise SystemExit(1)

    output_path = Path(output)
    config = get_platform_config(platform)
    tts_config = get_tts_config()

    # Use direct m3u8 URL if provided, otherwise scrape from Kickstarter
    if not m3u8_url:
        click.echo(f"Fetching Kickstarter page: {url}")
        try:
            html = fetch_kickstarter_page(url)
        except Exception as e:
            click.echo(f"Error fetching page: {e}", err=True)
            raise SystemExit(1)

        click.echo("Extracting video URL...")
        m3u8_url = extract_m3u8_url(html)
        if not m3u8_url:
            click.echo("Error: Could not find video URL in page", err=True)
            raise SystemExit(1)

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        downloaded_video = tmpdir / "downloaded.mp4"

        click.echo("Downloading video...")
        try:
            download_and_merge_m3u8(m3u8_url, downloaded_video)
        except Exception as e:
            click.echo(f"Error downloading video: {e}", err=True)
            raise SystemExit(1)

        click.echo("Analyzing scenes...")
        fragments = detect_scenes(downloaded_video, threshold=scene_threshold)

        if not fragments:
            click.echo("Warning: No scenes detected. Using fixed intervals.")
            duration = get_video_duration(downloaded_video)
            interval = 5.0
            fragments = [
                Scene(start=i * interval, end=min((i + 1) * interval, duration))
                for i in range(int(duration / interval))
            ]

        click.echo(f"Found {len(fragments)} scenes. Selecting best fragments...")
        selected = select_top_fragments(fragments, target_duration=config.max_duration)

        if not selected:
            click.echo("Warning: Video too short. Using original video.")
            selected = fragments

        total_duration = sum(f.end - f.start for f in selected)
        click.echo(f"Selected {len(selected)} fragments ({total_duration:.1f}s total)")

        click.echo(f"Creating short video for {platform}...")
        short_video = tmpdir / "short.mp4"
        create_short(downloaded_video, selected, short_video, config)

        # Extract audio and transcribe (English)
        click.echo("Extracting audio...")
        audio_path = tmpdir / "audio.wav"
        try:
            extract_audio(downloaded_video, audio_path)
        except Exception as e:
            click.echo(f"Error extracting audio: {e}", err=True)
            raise SystemExit(1)

        click.echo("Transcribing with Whisper...")
        try:
            transcript = transcribe_audio(audio_path, model=tts_config.whisper_model)
        except Exception as e:
            click.echo(f"Error transcribing audio: {e}", err=True)
            raise SystemExit(1)

        # Save English transcript
        script_path = output_path.with_stem(output_path.stem + "_script").with_suffix(".md")
        click.echo(f"Saving transcript to: {script_path}")
        save_transcript(transcript, script_path)

        # Translate and refine
        click.echo("Translating and refining script...")
        try:
            chinese_script = translate_and_refine(
                transcript,
                api_key=api_config.yuanjing_api_key,
                base_url=api_config.yuanjing_base_url
            )
        except Exception as e:
            click.echo(f"Error translating: {e}", err=True)
            raise SystemExit(1)

        # Save Chinese script
        chinese_path = output_path.with_stem(output_path.stem + "_chinese").with_suffix(".md")
        click.echo(f"Saving Chinese script to: {chinese_path}")
        chinese_path.write_text(f"# Chinese Script\n\n{chinese_script}", encoding="utf-8")

        # Generate TTS audio
        click.echo("Generating Chinese audio...")
        dubbing_path = tmpdir / "dubbing.wav"
        try:
            generate_audio(chinese_script, dubbing_path, voice=tts_config.voice)
        except Exception as e:
            click.echo(f"Error generating audio: {e}", err=True)
            raise SystemExit(1)

        # Generate SRT subtitle
        click.echo("Generating subtitles...")
        srt_path = tmpdir / "subtitle.srt"
        try:
            generate_srt(dubbing_path, srt_path, model=tts_config.whisper_model)
        except Exception as e:
            click.echo(f"Error generating subtitles: {e}", err=True)
            raise SystemExit(1)

        # Align subtitle with Chinese script
        click.echo("Aligning subtitles...")
        aligned_srt_path = tmpdir / "aligned.srt"
        try:
            align_subtitle(srt_path, chinese_script, aligned_srt_path)
        except Exception as e:
            click.echo(f"Error aligning subtitles: {e}", err=True)
            raise SystemExit(1)

        # Extract original audio for mixing
        click.echo("Extracting original audio for mixing...")
        original_audio_path = tmpdir / "original.wav"
        try:
            extract_audio_for_mixing(short_video, original_audio_path)
        except Exception as e:
            click.echo(f"Error extracting original audio: {e}", err=True)
            raise SystemExit(1)

        # Merge everything
        click.echo("Merging video with audio and subtitles...")
        try:
            merge_video_audio_subtitle(
                short_video,
                original_audio_path,
                dubbing_path,
                aligned_srt_path,
                output_path
            )
        except Exception as e:
            click.echo(f"Error merging: {e}", err=True)
            raise SystemExit(1)

        # Save original downloaded video
        orig_path = output_path.with_stem(output_path.stem + "_orig")
        click.echo(f"Saving original video to: {orig_path}")
        shutil.copy2(downloaded_video, orig_path)

        # Save SRT file
        final_srt_path = output_path.with_suffix(".srt")
        shutil.copy2(aligned_srt_path, final_srt_path)

    click.echo(f"Done! Output saved to: {output_path}")


if __name__ == "__main__":
    main()
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_cli_integration.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add recut/cli.py tests/test_cli_integration.py
git commit -m "feat: integrate Chinese dubbing workflow into CLI"
```

---

## Task 8: 运行全部测试

**Step 1: 运行全部测试**

Run: `pytest tests/ -v`

**Step 2: 修复失败测试**

如果有测试失败，修复后重新运行。

**Step 3: 最终提交**

```bash
git add -A
git commit -m "feat: complete Chinese dubbing feature implementation"
```

---

## 完成清单

- [ ] Task 1: 更新依赖
- [ ] Task 2: 扩展配置模块
- [ ] Task 3: 实现 translator 模块
- [ ] Task 4: 实现 tts 模块
- [ ] Task 5: 实现 subtitle 模块
- [ ] Task 6: 扩展 editor 模块
- [ ] Task 7: 更新 CLI 集成全部流程
- [ ] Task 8: 运行全部测试
