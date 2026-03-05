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
