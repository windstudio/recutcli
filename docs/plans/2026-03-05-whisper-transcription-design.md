# Whisper Transcription Feature Design

## Overview
Add audio transcription capability using Whisper to extract and transcribe spoken content from downloaded videos.

## Requirements
- Extract audio from downloaded video after `download_and_merge_m3u8`
- Transcribe audio using openai-whisper (local)
- Save transcript as MD file with `_script` suffix

## Architecture

### New Module: `recut/transcriber.py`

```python
def extract_audio(video_path: Path, audio_path: Path) -> Path:
    """Extract audio from video to WAV file using ffmpeg."""

def transcribe_audio(audio_path: Path, model: str = "small") -> str:
    """Transcribe audio using Whisper, return text."""

def save_transcript(transcript: str, output_path: Path) -> Path:
    """Save transcript to MD file."""
```

### Modify: `recut/cli.py`

Insert transcription step after `create_short()`, before `shutil.copy2()`:
1. Extract audio to temp file
2. Transcribe with Whisper
3. Save transcript to `{output_stem}_script.md`

## Output Format

```markdown
# Transcript

[Transcribed text]
```

## Dependencies

Add to `pyproject.toml`:
- `openai-whisper>=20250625`

## File Output Example

Given output path `AI_Notetaker.mp4`:
- `AI_Notetaker.mp4` - short video
- `AI_Notetaker_orig.mp4` - original full video
- `AI_Notetaker_script.md` - transcript
