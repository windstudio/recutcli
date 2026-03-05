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

        with patch("recut.tts._ensure_model_files") as mock_ensure, \
             patch("recut.tts.PiperVoice") as mock_voice_class:
            mock_ensure.return_value = (Path("model.onnx"), Path("model.onnx.json"))
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

        with patch("recut.tts._ensure_model_files") as mock_ensure, \
             patch("recut.tts.PiperVoice") as mock_voice_class:
            mock_ensure.return_value = (Path("model.onnx"), Path("model.onnx.json"))
            mock_voice = MagicMock()
            mock_voice_class.load.return_value = mock_voice

            generate_audio("测试", output_path, voice="zh_CN-male-medium")

            # Verify _ensure_model_files was called with the custom voice
            mock_ensure.assert_called_once_with("zh_CN-male-medium")


def test_generate_audio_raises_on_error():
    """Test that generate_audio raises on TTS error."""
    from recut.tts import generate_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        with patch("recut.tts._ensure_model_files") as mock_ensure:
            mock_ensure.side_effect = RuntimeError("Model not found")

            with pytest.raises(RuntimeError, match="TTS generation failed"):
                generate_audio("测试", output_path)
