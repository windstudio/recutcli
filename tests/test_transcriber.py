# tests/test_transcriber.py
"""Tests for transcriber module."""

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from recut.transcriber import extract_audio, transcribe_audio
from recut.downloader import get_ffmpeg_path


def test_extract_audio_creates_wav_file():
    """Test that extract_audio creates a WAV file from video."""
    # Skip if ffmpeg not available
    try:
        subprocess.run([get_ffmpeg_path(), "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("ffmpeg not available")

    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        # Create a silent test video (1 second)
        video_path = tmpdir / "test.mp4"
        subprocess.run([
            get_ffmpeg_path(), "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1", "-c:a", "aac", "-y", str(video_path)
        ], capture_output=True, check=True)

        audio_path = tmpdir / "audio.wav"
        result = extract_audio(video_path, audio_path)

        assert result == audio_path
        assert audio_path.exists()


def test_transcribe_audio_returns_text():
    """Test that transcribe_audio returns text from audio."""
    with TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        # Create a silent WAV file for testing
        audio_path = tmpdir / "test.wav"
        subprocess.run([
            get_ffmpeg_path(), "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1", "-c:a", "pcm_s16le", "-y", str(audio_path)
        ], capture_output=True, check=True)

        # Whisper will return empty or minimal text for silent audio
        result = transcribe_audio(audio_path, model="small")

        assert isinstance(result, str)
