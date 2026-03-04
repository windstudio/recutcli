# Whisper Transcription Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add audio transcription capability using Whisper to extract and transcribe spoken content from downloaded videos.

**Architecture:** Create new `transcriber.py` module with audio extraction and transcription functions, integrate into CLI pipeline after video download.

**Tech Stack:** Python, openai-whisper, ffmpeg (already available)

---

### Task 1: Add openai-whisper dependency

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add dependency to pyproject.toml**

```toml
dependencies = [
    "click>=8.0.0",
    "requests>=2.28.0",
    "beautifulsoup4>=4.12.0",
    "ffmpeg-python>=0.2.0",
    "imageio-ffmpeg>=0.4.0",
    "openai-whisper>=20250625",
]
```

**Step 2: Install dependency**

Run: `pip install -e .`
Expected: Successfully installed with openai-whisper

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add openai-whisper dependency"
```

---

### Task 2: Create transcriber module - extract_audio function

**Files:**
- Create: `recut/transcriber.py`
- Create: `tests/test_transcriber.py`

**Step 1: Write the failing test**

```python
# tests/test_transcriber.py
"""Tests for transcriber module."""

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from recut.transcriber import extract_audio


def test_extract_audio_creates_wav_file():
    """Test that extract_audio creates a WAV file from video."""
    # Skip if ffmpeg not available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("ffmpeg not available")

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        # Create a silent test video (1 second)
        video_path = tmpdir / "test.mp4"
        subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1", "-c:a", "aac", "-y", str(video_path)
        ], capture_output=True, check=True)

        audio_path = tmpdir / "audio.wav"
        result = extract_audio(video_path, audio_path)

        assert result == audio_path
        assert audio_path.exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_transcriber.py::test_extract_audio_creates_wav_file -v`
Expected: FAIL with "cannot import name 'extract_audio'"

**Step 3: Write minimal implementation**

```python
# recut/transcriber.py
"""Audio extraction and transcription using Whisper."""

from pathlib import Path
import subprocess

from recut.downloader import get_ffmpeg_path


def extract_audio(video_path: Path, audio_path: Path) -> Path:
    """Extract audio from video to WAV file.

    Args:
        video_path: Path to source video
        audio_path: Path to output audio file

    Returns:
        Path to the extracted audio file
    """
    video_path = Path(video_path)
    audio_path = Path(audio_path)

    cmd = [
        get_ffmpeg_path(),
        "-i", str(video_path),
        "-vn",  # No video
        "-acodec", "pcm_s16le",  # WAV format
        "-ar", "16000",  # 16kHz sample rate (Whisper optimal)
        "-ac", "1",  # Mono
        "-y",  # Overwrite
        str(audio_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return audio_path
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_transcriber.py::test_extract_audio_creates_wav_file -v`
Expected: PASS

**Step 5: Commit**

```bash
git add recut/transcriber.py tests/test_transcriber.py
git commit -m "feat: add extract_audio function for audio extraction"
```

---

### Task 3: Add transcribe_audio function

**Files:**
- Modify: `recut/transcriber.py`
- Modify: `tests/test_transcriber.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_transcriber.py

from recut.transcriber import transcribe_audio


def test_transcribe_audio_returns_text():
    """Test that transcribe_audio returns text from audio."""
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        # Create a silent WAV file for testing
        audio_path = tmpdir / "test.wav"
        subprocess.run([
            "ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1", "-c:a", "pcm_s16le", "-y", str(audio_path)
        ], capture_output=True, check=True)

        # Whisper will return empty or minimal text for silent audio
        result = transcribe_audio(audio_path, model="small")

        assert isinstance(result, str)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_transcriber.py::test_transcribe_audio_returns_text -v`
Expected: FAIL with "cannot import name 'transcribe_audio'"

**Step 3: Write minimal implementation**

```python
# Add to recut/transcriber.py

import whisper


def transcribe_audio(audio_path: Path, model: str = "small") -> str:
    """Transcribe audio using Whisper.

    Args:
        audio_path: Path to audio file
        model: Whisper model size (tiny, base, small, medium, large)

    Returns:
        Transcribed text
    """
    audio_path = Path(audio_path)

    # Load model and transcribe
    whisper_model = whisper.load_model(model)
    result = whisper_model.transcribe(str(audio_path))

    return result["text"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_transcriber.py::test_transcribe_audio_returns_text -v`
Expected: PASS (may take time to download model on first run)

**Step 5: Commit**

```bash
git add recut/transcriber.py tests/test_transcriber.py
git commit -m "feat: add transcribe_audio function using Whisper"
```

---

### Task 4: Add save_transcript function

**Files:**
- Modify: `recut/transcriber.py`
- Modify: `tests/test_transcriber.py`

**Step 1: Write the failing test**

```python
# Add to tests/test_transcriber.py

from recut.transcriber import save_transcript


def test_save_transcript_creates_md_file():
    """Test that save_transcript creates a markdown file."""
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        output_path = tmpdir / "transcript.md"

        result = save_transcript("Hello world", output_path)

        assert result == output_path
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "# Transcript" in content
        assert "Hello world" in content
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_transcriber.py::test_save_transcript_creates_md_file -v`
Expected: FAIL with "cannot import name 'save_transcript'"

**Step 3: Write minimal implementation**

```python
# Add to recut/transcriber.py

def save_transcript(transcript: str, output_path: Path) -> Path:
    """Save transcript to markdown file.

    Args:
        transcript: Transcribed text
        output_path: Path to output markdown file

    Returns:
        Path to the saved file
    """
    output_path = Path(output_path)

    content = f"""# Transcript

{transcript}
"""
    output_path.write_text(content, encoding="utf-8")
    return output_path
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_transcriber.py::test_save_transcript_creates_md_file -v`
Expected: PASS

**Step 5: Commit**

```bash
git add recut/transcriber.py tests/test_transcriber.py
git commit -m "feat: add save_transcript function"
```

---

### Task 5: Integrate transcription into CLI

**Files:**
- Modify: `recut/cli.py`

**Step 1: Add imports**

```python
# Add to imports in recut/cli.py
from recut.transcriber import extract_audio, transcribe_audio, save_transcript
```

**Step 2: Add transcription step in main function**

After `create_short()` call and before `shutil.copy2()`, add:

```python
        # Extract audio and transcribe
        click.echo("Extracting audio...")
        audio_path = tmpdir / "audio.wav"
        extract_audio(downloaded_video, audio_path)

        click.echo("Transcribing with Whisper...")
        transcript = transcribe_audio(audio_path)

        # Save transcript
        script_path = output_path.with_stem(output_path.stem + "_script").with_suffix(".md")
        click.echo(f"Saving transcript to: {script_path}")
        save_transcript(transcript, script_path)
```

**Step 3: Run existing tests to verify no breakage**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add recut/cli.py
git commit -m "feat: integrate Whisper transcription into CLI pipeline"
```

---

### Task 6: Final verification

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

**Step 2: Manual integration test**

Run: `recut <kickstarter_url> -o test.mp4`
Expected:
- `test.mp4` created (short video)
- `test_orig.mp4` created (original video)
- `test_script.md` created (transcript)

**Step 3: Push changes**

```bash
git push origin main
```
