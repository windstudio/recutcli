# recut/transcriber.py
"""Audio extraction and transcription using Whisper."""

from pathlib import Path
import subprocess

import whisper

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
    try:
        subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to extract audio from {video_path}: {e.stderr.decode()}")
    return audio_path


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
