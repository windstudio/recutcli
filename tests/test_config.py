# tests/test_config.py
"""Tests for config module."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from recut.config import (
    get_platform_config,
    PlatformConfig,
    TTSConfig,
    APIConfig,
    get_api_config,
    get_tts_config,
    load_dotenv_config,
)


def test_get_tiktok_config():
    config = get_platform_config("tiktok")
    assert config.width == 1080
    assert config.height == 1920
    assert config.max_duration == 30  # Default duration changed to 30


def test_get_instagram_config():
    config = get_platform_config("instagram")
    assert config.width == 1080
    assert config.height == 1920
    assert config.max_duration == 30


def test_get_reels_config():
    config = get_platform_config("reels")
    assert config.width == 1080
    assert config.height == 1920
    assert config.max_duration == 30


def test_custom_duration():
    """Test that custom duration overrides default."""
    config = get_platform_config("tiktok", duration=60)
    assert config.width == 1080
    assert config.height == 1920
    assert config.max_duration == 60


def test_invalid_platform_raises():
    with pytest.raises(ValueError, match="Unknown platform"):
        get_platform_config("youtube")


def test_tts_config_defaults():
    """Test TTSConfig has correct defaults."""
    config = TTSConfig()
    assert config.engine == "edge"
    assert config.voice == "zh-CN-XiaoxiaoNeural"
    assert config.coqui_voice == "tts_models/zh-CN/baker/tacotron2-DDC"
    assert config.piper_voice == "zh_CN-huayan-medium"
    assert config.whisper_model == "small"


def test_tts_config_from_env(monkeypatch):
    """Test TTSConfig reads from environment variables."""
    monkeypatch.setenv("TTS_ENGINE", "piper")
    monkeypatch.setenv("TTS_VOICE", "zh-CN-YunxiNeural")
    monkeypatch.setenv("COQUI_VOICE", "tts_models/zh-CN/custom")
    monkeypatch.setenv("PIPER_VOICE", "zh_CN-male-medium")
    monkeypatch.setenv("WHISPER_MODEL", "medium")

    config = get_tts_config()
    assert config.engine == "piper"
    assert config.voice == "zh-CN-YunxiNeural"
    assert config.coqui_voice == "tts_models/zh-CN/custom"
    assert config.piper_voice == "zh_CN-male-medium"
    assert config.whisper_model == "medium"


def test_api_config_defaults():
    """Test APIConfig has correct defaults."""
    config = APIConfig()
    assert config.llm_api_key == ""
    assert "ai-yuanjing" in config.llm_api_url


def test_api_config_from_env(monkeypatch):
    """Test APIConfig reads from environment variables."""
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_API_URL", "https://api.example.com/v1")
    monkeypatch.setenv("LLM_MODEL", "gpt-4")

    config = get_api_config()
    assert config.llm_api_key == "test-key"
    assert config.llm_api_url == "https://api.example.com/v1"
    assert config.llm_model == "gpt-4"


def test_load_dotenv():
    """Test that load_dotenv loads .env file."""
    with TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("LLM_API_KEY=dotenv-key\n")

        # Clear any existing value
        os.environ.pop("LLM_API_KEY", None)

        # Load the .env file
        load_dotenv_config(env_file)

        # Verify the value was loaded
        assert os.environ.get("LLM_API_KEY") == "dotenv-key"

        # Cleanup
        os.environ.pop("LLM_API_KEY", None)


def test_api_config_reads_llm_env_vars(monkeypatch):
    """Test that APIConfig reads LLM_API_KEY, LLM_API_URL, LLM_MODEL from env."""
    monkeypatch.setenv("LLM_API_KEY", "test-key-123")
    monkeypatch.setenv("LLM_API_URL", "https://api.example.com/v1")
    monkeypatch.setenv("LLM_MODEL", "gpt-4")

    config = get_api_config()

    assert config.llm_api_key == "test-key-123"
    assert config.llm_api_url == "https://api.example.com/v1"
    assert config.llm_model == "gpt-4"


def test_api_config_default_values(monkeypatch):
    """Test default values when no env vars set."""
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    config = get_api_config()

    assert config.llm_api_key == ""
    assert config.llm_api_url == "https://maas-api.ai-yuanjing.com/openapi/compatible-mode/v1"
    assert config.llm_model == "glm-5"
