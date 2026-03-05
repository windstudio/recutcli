"""Tests for tts module."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

import pytest


def test_generate_audio_calls_edge_by_default():
    """Test that generate_audio calls Edge TTS by default."""
    from recut.tts import generate_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        with patch("recut.tts._generate_edge_audio") as mock_edge, \
             patch("recut.tts.get_tts_config") as mock_config:
            mock_config.return_value = MagicMock(engine="edge", voice="test-voice")
            mock_edge.return_value = output_path

            result = generate_audio("测试文本", output_path)

            assert result == output_path
            mock_edge.assert_called_once_with("测试文本", output_path, "test-voice")


def test_generate_audio_calls_coqui_when_specified():
    """Test that generate_audio calls Coqui TTS when engine='coqui'."""
    from recut.tts import generate_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        with patch("recut.tts._generate_coqui_audio") as mock_coqui, \
             patch("recut.tts.get_tts_config") as mock_config:
            mock_config.return_value = MagicMock(engine="coqui", coqui_voice="test-coqui-voice")
            mock_coqui.return_value = output_path

            result = generate_audio("测试文本", output_path, engine="coqui")

            assert result == output_path
            mock_coqui.assert_called_once_with("测试文本", output_path, "test-coqui-voice")


def test_generate_audio_calls_piper_when_specified():
    """Test that generate_audio calls Piper TTS when engine='piper'."""
    from recut.tts import generate_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        with patch("recut.tts._generate_piper_audio") as mock_piper, \
             patch("recut.tts.get_tts_config") as mock_config:
            mock_config.return_value = MagicMock(engine="piper", piper_voice="test-piper-voice")
            mock_piper.return_value = output_path

            result = generate_audio("测试文本", output_path, engine="piper")

            assert result == output_path
            mock_piper.assert_called_once_with("测试文本", output_path, "test-piper-voice")


def test_generate_audio_uses_custom_voice():
    """Test that generate_audio uses custom voice when provided."""
    from recut.tts import generate_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        with patch("recut.tts._generate_edge_audio") as mock_edge, \
             patch("recut.tts.get_tts_config") as mock_config:
            mock_config.return_value = MagicMock(engine="edge", voice="default-voice")
            mock_edge.return_value = output_path

            generate_audio("测试", output_path, voice="custom-voice")

            mock_edge.assert_called_once_with("测试", output_path, "custom-voice")


def test_generate_audio_edge_raises_on_error():
    """Test that generate_audio propagates Edge TTS error."""
    from recut.tts import generate_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        with patch("recut.tts._generate_edge_audio") as mock_edge, \
             patch("recut.tts.get_tts_config") as mock_config:
            mock_config.return_value = MagicMock(engine="edge", voice="test-voice")
            mock_edge.side_effect = RuntimeError("Network error")

            with pytest.raises(RuntimeError, match="Network error"):
                generate_audio("测试", output_path, engine="edge")


def test_generate_audio_coqui_raises_on_error():
    """Test that generate_audio propagates Coqui TTS error."""
    from recut.tts import generate_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        with patch("recut.tts._generate_coqui_audio") as mock_coqui, \
             patch("recut.tts.get_tts_config") as mock_config:
            mock_config.return_value = MagicMock(engine="coqui", coqui_voice="test-voice")
            mock_coqui.side_effect = RuntimeError("Model not found")

            with pytest.raises(RuntimeError, match="Model not found"):
                generate_audio("测试", output_path, engine="coqui")


def test_generate_audio_piper_raises_on_error():
    """Test that generate_audio propagates Piper TTS error."""
    from recut.tts import generate_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        with patch("recut.tts._generate_piper_audio") as mock_piper, \
             patch("recut.tts.get_tts_config") as mock_config:
            mock_config.return_value = MagicMock(engine="piper", piper_voice="test-voice")
            mock_piper.side_effect = RuntimeError("Model not found")

            with pytest.raises(RuntimeError, match="Model not found"):
                generate_audio("测试", output_path, engine="piper")


def test_ensure_piper_model_files_downloads_missing_model():
    """Test that _ensure_piper_model_files downloads model if missing."""
    from recut.tts import _ensure_piper_model_files

    with TemporaryDirectory() as tmpdir:
        import recut.tts
        original_dir = recut.tts.PIPER_MODELS_DIR
        recut.tts.PIPER_MODELS_DIR = Path(tmpdir)

        try:
            with patch("urllib.request.urlretrieve") as mock_download:
                onnx_path, json_path = _ensure_piper_model_files("zh_CN-huayan-medium")

                # Should download both onnx and json files
                assert mock_download.call_count == 2
                assert onnx_path.name == "zh_CN-huayan-medium.onnx"
                assert json_path.name == "zh_CN-huayan-medium.onnx.json"
        finally:
            recut.tts.PIPER_MODELS_DIR = original_dir
