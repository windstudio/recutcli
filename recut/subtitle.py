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


def _split_by_punctuation(text: str) -> list[str]:
    """Split text by Chinese punctuation marks for better subtitle display.

    Args:
        text: Text to split

    Returns:
        List of text segments, each ending with punctuation (except possibly the last)
    """
    # Chinese punctuation marks that should end a subtitle line
    punctuations = "，。！？、；：""''）】》"

    segments = []
    current = ""

    for char in text:
        current += char
        if char in punctuations:
            segments.append(current)
            current = ""

    # Add remaining text if any
    if current.strip():
        segments.append(current)

    return segments


def align_subtitle(
    srt_path: Path,
    expected_text: str,
    output_path: Path
) -> Path:
    """Align subtitle text with expected text, creating segments per line.

    This function takes an SRT file with timestamps from Whisper transcription
    and creates new segments based on the expected text lines.

    Each line in expected_text becomes one subtitle segment, with time
    distributed proportionally based on character count.
    Within each segment, text is split by Chinese punctuation for proper
    line breaks in display.

    Args:
        srt_path: Path to input SRT file (used for total duration)
        expected_text: Expected correct text (multi-line, each line = one segment)
        output_path: Path to output SRT file

    Returns:
        Path to aligned SRT file
    """
    srt_path = Path(srt_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Parse original SRT to get total duration
    content = srt_path.read_text(encoding="utf-8")
    blocks = content.strip().split("\n\n")

    total_duration = 0.0
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 2:
            timestamp = lines[1]
            try:
                start_str, end_str = timestamp.split(" --> ")
                start = _parse_timestamp(start_str.strip())
                end = _parse_timestamp(end_str.strip())
                total_duration = max(total_duration, end)
            except Exception:
                continue

    if total_duration == 0:
        total_duration = 30.0  # Default fallback

    # Get text lines (each line becomes one subtitle segment)
    text_lines = [line.strip() for line in expected_text.strip().split("\n") if line.strip()]

    if not text_lines:
        output_path.write_text("", encoding="utf-8")
        return output_path

    # Calculate duration per character for proportional distribution
    total_chars = sum(len(line) for line in text_lines)
    char_duration = total_duration / total_chars if total_chars > 0 else total_duration / len(text_lines)

    # Generate new subtitle blocks
    new_blocks = []
    current_time = 0.0

    for i, line in enumerate(text_lines):
        # Calculate duration based on character count
        line_duration = len(line) * char_duration
        start_time = current_time
        end_time = current_time + line_duration

        # Format timestamps
        start_ts = _format_timestamp(start_time)
        end_ts = _format_timestamp(end_time)

        # Split line by punctuation for proper display line breaks
        segments = _split_by_punctuation(line)
        # Join segments with \N (SRT line break)
        display_text = "\\N".join(segments)

        new_blocks.append(f"{i + 1}\n{start_ts} --> {end_ts}\n{display_text}")
        current_time = end_time

    output_path.write_text("\n\n".join(new_blocks) + "\n", encoding="utf-8")
    return output_path


def _parse_timestamp(timestamp: str) -> float:
    """Parse SRT timestamp to seconds.

    Args:
        timestamp: SRT timestamp string (HH:MM:SS,mmm)

    Returns:
        Time in seconds
    """
    timestamp = timestamp.strip()
    time_part, millis = timestamp.rsplit(",", 1)
    hours, minutes, seconds = time_part.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000
