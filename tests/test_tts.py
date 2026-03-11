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


def test_generate_audio_calls_minimax_when_specified():
    """Test that generate_audio calls MiniMax TTS when engine='minimax'."""
    from recut.tts import generate_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        with patch("recut.tts._generate_minimax_audio") as mock_minimax, \
             patch("recut.tts.get_tts_config") as mock_config:
            mock_config.return_value = MagicMock(engine="minimax")
            mock_minimax.return_value = output_path

            result = generate_audio("测试文本", output_path, engine="minimax")

            assert result == output_path
            mock_minimax.assert_called_once_with("测试文本", output_path, None)


def test_generate_audio_minimax_raises_on_error():
    """Test that generate_audio propagates MiniMax TTS error."""
    from recut.tts import generate_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        with patch("recut.tts._generate_minimax_audio") as mock_minimax, \
             patch("recut.tts.get_tts_config") as mock_config:
            mock_config.return_value = MagicMock(engine="minimax")
            mock_minimax.side_effect = RuntimeError("API error")

            with pytest.raises(RuntimeError, match="API error"):
                generate_audio("测试", output_path, engine="minimax")


def test_generate_minimax_audio_requires_api_key():
    """Test that MiniMax TTS raises error when API key is not set."""
    from recut.tts import _generate_minimax_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        with patch("recut.config.get_minimax_config") as mock_config:
            mock_config.return_value = MagicMock(api_key="", api_url="https://test.com", voice_id="test-voice")

            with pytest.raises(RuntimeError, match="MINIMAX_API_KEY not set"):
                _generate_minimax_audio("测试", output_path)


def test_generate_minimax_audio_success():
    """Test successful MiniMax TTS audio generation."""
    from recut.tts import _generate_minimax_audio

    with TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output.wav"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"audio": "52494646", "status": 2},  # "RIFF" in hex
            "base_resp": {"status_code": 0, "status_msg": "success"}
        }

        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response
        mock_requests.RequestException = Exception

        with patch.dict("sys.modules", {"requests": mock_requests}), \
             patch("recut.config.get_minimax_config") as mock_config:
            mock_config.return_value = MagicMock(
                api_key="test-key",
                api_url="https://test.com",
                voice_id="test-voice"
            )

            result = _generate_minimax_audio("测试", output_path)

            assert result == output_path
            assert output_path.exists()
            assert output_path.read_bytes() == bytes.fromhex("52494646")
