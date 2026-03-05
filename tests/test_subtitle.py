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


def test_split_by_punctuation():
    """Test that _split_by_punctuation splits text at Chinese punctuation."""
    from recut.subtitle import _split_by_punctuation

    # Test with various Chinese punctuation
    text = "这是第一句，这是第二句。这是第三句！"
    segments = _split_by_punctuation(text)
    assert len(segments) == 3
    assert segments[0] == "这是第一句，"
    assert segments[1] == "这是第二句。"
    assert segments[2] == "这是第三句！"


def test_split_by_punctuation_no_trailing():
    """Test _split_by_punctuation with text not ending in punctuation."""
    from recut.subtitle import _split_by_punctuation

    text = "第一句，第二句没有标点"
    segments = _split_by_punctuation(text)
    assert len(segments) == 2
    assert segments[0] == "第一句，"
    assert segments[1] == "第二句没有标点"


def test_align_subtitle_with_punctuation_split():
    """Test that align_subtitle splits text by punctuation for display."""
    from recut.subtitle import align_subtitle

    with TemporaryDirectory() as tmpdir:
        srt_path = Path(tmpdir) / "input.srt"
        srt_path.write_text("""1
00:00:00,000 --> 00:00:05,000
错误文字
""", encoding="utf-8")
        output_path = Path(tmpdir) / "output.srt"

        # Text with punctuation should be split into multiple display lines
        expected_text = "第一句，第二句。第三句！"
        result = align_subtitle(srt_path, expected_text, output_path)

        content = output_path.read_text(encoding="utf-8")
        # Should contain SRT line break character \N
        assert "\\N" in content
        assert "第一句，" in content
        assert "第二句。" in content


def test_align_subtitle_corrects_text():
    """Test that align_subtitle creates segments per line with proportional timing."""
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

        # Multi-line text: each line becomes one segment
        expected_text = "正确文字\n另一段正确"
        result = align_subtitle(srt_path, expected_text, output_path)

        assert result == output_path
        content = output_path.read_text(encoding="utf-8")
        assert "正确文字" in content
        assert "另一段正确" in content
        assert "错误文字" not in content
        # Should have 2 segments with timestamps starting from 0
        assert "00:00:00,000 -->" in content
        # Total duration is 4 seconds, distributed by character count


def test_align_subtitle_handles_mismatch():
    """Test align_subtitle creates correct number of segments from text lines."""
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

        # Single-line text creates one segment
        expected_text = "简短文本"
        result = align_subtitle(srt_path, expected_text, output_path)

        assert result == output_path
        content = output_path.read_text(encoding="utf-8")
        # Should have exactly one segment
        assert content.count("\n\n") == 0  # Only one block, no double newlines
        assert "简短文本" in content
        # Time should be distributed based on character count
        assert "00:00:00,000 -->" in content
