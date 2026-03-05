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

    This function takes an SRT file with timestamps from Whisper transcription
    and replaces the text with the expected correct text, distributing it
    proportionally across the segments.

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

    # Calculate total duration from timestamps
    total_duration = 0.0
    segments_info = []
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            timestamp = lines[1]
            try:
                # Parse timestamps (format: HH:MM:SS,mmm --> HH:MM:SS,mmm)
                start_str, end_str = timestamp.split(" --> ")
                start = _parse_timestamp(start_str.strip())
                end = _parse_timestamp(end_str.strip())
                duration = end - start
                total_duration += duration
                segments_info.append({
                    "index": lines[0],
                    "timestamp": timestamp,
                    "duration": duration,
                    "start": start,
                    "end": end
                })
            except Exception:
                continue

    if not segments_info:
        # Fallback: just write the expected text as single segment
        output_path.write_text(f"1\n00:00:00,000 --> 00:00:30,000\n{expected_text}\n", encoding="utf-8")
        return output_path

    # Remove spaces and punctuation for better character distribution
    # Chinese text should be distributed by characters, not words
    chars = [c for c in expected_text if not c.isspace()]
    total_chars = len(chars)

    if total_chars == 0:
        output_path.write_text("", encoding="utf-8")
        return output_path

    # Distribute characters proportionally by segment duration
    new_blocks = []
    char_idx = 0

    for i, seg in enumerate(segments_info):
        # Calculate how many characters this segment should have
        if i < len(segments_info) - 1:
            # Proportional to duration
            seg_chars = int(total_chars * seg["duration"] / total_duration)
        else:
            # Last segment gets remaining characters
            seg_chars = total_chars - char_idx

        # Get characters for this segment
        end_idx = min(char_idx + seg_chars, total_chars)
        segment_text = "".join(chars[char_idx:end_idx])
        char_idx = end_idx

        # Skip empty segments
        if segment_text:
            new_blocks.append(f"{seg['index']}\n{seg['timestamp']}\n{segment_text}")

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
