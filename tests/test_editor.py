# tests/test_editor.py
from recut.editor import format_timestamp

def test_format_timestamp_seconds():
    assert format_timestamp(5.5) == "00:00:05.500"

def test_format_timestamp_minutes():
    assert format_timestamp(65.5) == "00:01:05.500"

def test_format_timestamp_hours():
    assert format_timestamp(3661.5) == "01:01:01.500"


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

        # Create test video with video and audio
        video_path = tmpdir / "video.mp4"
        subprocess.run([
            get_ffmpeg_path(), "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-f", "lavfi", "-i", "anullsrc=r=16000:cl=mono",
            "-t", "1", "-c:v", "libx264", "-c:a", "aac", "-y", str(video_path)
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
