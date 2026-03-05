# tests/test_config.py
from recut.config import get_platform_config, PlatformConfig
import pytest


def test_get_tiktok_config():
    config = get_platform_config("tiktok")
    assert config.width == 1080
    assert config.height == 1920
    assert config.max_duration == 25


def test_get_instagram_config():
    config = get_platform_config("instagram")
    assert config.width == 1080
    assert config.height == 1920
    assert config.max_duration == 25


def test_get_reels_config():
    config = get_platform_config("reels")
    assert config.width == 1080
    assert config.height == 1920
    assert config.max_duration == 25


def test_invalid_platform_raises():
    with pytest.raises(ValueError, match="Unknown platform"):
        get_platform_config("youtube")


import os
from pathlib import Path
from tempfile import TemporaryDirectory


def test_tts_config_defaults():
    """Test TTSConfig has correct defaults."""
    from recut.config import TTSConfig
    config = TTSConfig()
    assert config.voice == "zh_CN-huayan-medium"
    assert config.whisper_model == "small"


def test_api_config_from_env():
    """Test APIConfig reads from environment and .env file."""
    from recut.config import APIConfig, get_api_config
    os.environ["YUANJING_API_KEY"] = "test-key"
    config = get_api_config()
    assert config.yuanjing_api_key == "test-key"
    assert "ai-yuanjing" in config.yuanjing_base_url
    del os.environ["YUANJING_API_KEY"]


def test_load_dotenv():
    """Test that load_dotenv loads .env file."""
    from recut.config import load_dotenv_config

    with TemporaryDirectory() as tmpdir:
        env_file = Path(tmpdir) / ".env"
        env_file.write_text("YUANJING_API_KEY=dotenv-key\n")

        # Should not raise
        load_dotenv_config(env_file)
